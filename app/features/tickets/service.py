import asyncio
import heapq
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.features.agents.models import Agent
from app.features.tickets.models import Ticket


settings = get_settings()
THREAD_POOL = ThreadPoolExecutor(max_workers=settings.max_workers_thread)
PROCESS_POOL = ProcessPoolExecutor(max_workers=settings.max_workers_process)


def classify_text(text: str) -> str:
    text_l = text.lower()
    if any(k in text_l for k in ("payment", "billing", "deducted", "invoice")):
        return "billing"
    if any(k in text_l for k in ("login", "password", "account", "otp")):
        return "account"
    if any(k in text_l for k in ("error", "bug", "crash", "not working")):
        return "technical"
    return "complaint"


def sentiment_score(text: str) -> str:
    text_l = text.lower()
    negatives = ("angry", "frustrated", "worst", "hate", "not working")
    positives = ("thanks", "great", "good", "resolved")
    if any(k in text_l for k in negatives):
        return "negative"
    if any(k in text_l for k in positives):
        return "positive"
    return "neutral"


def priority_score(text: str, sentiment: str) -> str:
    t = text.lower()
    points = 0
    if "urgent" in t or "asap" in t:
        points += 2
    if "payment" in t or "deducted" in t:
        points += 2
    if sentiment == "negative":
        points += 1
    if points >= 4:
        return "critical"
    if points >= 2:
        return "high"
    return "medium"


async def _least_loaded_agent_for_category(db: AsyncSession, category: str) -> int | None:
    stmt = select(Agent.id, Agent.skills, Agent.current_load).order_by(Agent.current_load.asc()).limit(100)
    rows = (await db.execute(stmt)).all()
    if not rows:
        return None

    heap: list[tuple[int, int]] = []
    for agent_id, skills, load in rows:
        skill_set = {s.strip().lower() for s in skills.split(",") if s.strip()}
        if category in skill_set or not skill_set:
            heapq.heappush(heap, (load, agent_id))

    if not heap:
        return None
    return heapq.heappop(heap)[1]


async def create_ticket_enriched(db: AsyncSession, title: str, description: str) -> Ticket:
    ticket = Ticket(title=title, description=description)
    db.add(ticket)
    await db.flush()

    loop = asyncio.get_running_loop()
    text = f"{title} {description}"

    category_fut = loop.run_in_executor(PROCESS_POOL, classify_text, text)
    sentiment_fut = loop.run_in_executor(THREAD_POOL, sentiment_score, text)
    category, sentiment = await asyncio.gather(category_fut, sentiment_fut)
    priority = await loop.run_in_executor(PROCESS_POOL, priority_score, text, sentiment)

    assignee_id = await _least_loaded_agent_for_category(db, category)

    ticket.category = category
    ticket.sentiment = sentiment
    ticket.priority = priority
    ticket.assignee_id = assignee_id
    ticket.status = "assigned" if assignee_id else "open"

    await db.commit()
    await db.refresh(ticket)
    return ticket


async def get_ticket_by_id(db: AsyncSession, ticket_id: int):
    stmt = (
        select(
            Ticket.id,
            Ticket.title,
            Ticket.description,
            Ticket.category,
            Ticket.priority,
            Ticket.sentiment,
            Ticket.status,
            Ticket.assignee_id,
        )
        .where(Ticket.id == ticket_id)
        .limit(1)
    )
    return (await db.execute(stmt)).first()


async def list_all_tickets(db: AsyncSession, limit: int = 100):
    stmt = (
        select(
            Ticket.id,
            Ticket.title,
            Ticket.description,
            Ticket.category,
            Ticket.priority,
            Ticket.sentiment,
            Ticket.status,
            Ticket.assignee_id,
        )
        .order_by(Ticket.id.desc())
        .limit(limit)
    )
    return (await db.execute(stmt)).all()
