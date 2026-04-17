import asyncio
import heapq
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.features.tickets.models import TicketConversation
from app.features.agents.models import Agent
from app.features.tickets.models import Ticket
from app.features.users.models import User


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

    ticket.category = category
    ticket.sentiment = sentiment
    ticket.priority = priority
    ticket.assignee_id = None
    ticket.status = "open"

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


async def list_assigned_tickets_for_user(db: AsyncSession, assignee_user_id: int, limit: int = 100):
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
        .where(Ticket.assignee_id == assignee_user_id)
        .order_by(Ticket.id.desc())
        .limit(limit)
    )
    return (await db.execute(stmt)).all()


async def assign_ticket_to_user(db: AsyncSession, ticket_id: int, assignee_user_id: int):
    ticket_exists_stmt = select(Ticket.id).where(Ticket.id == ticket_id).limit(1)
    ticket_exists = (await db.execute(ticket_exists_stmt)).first()
    if not ticket_exists:
        return None, "ticket_not_found"

    user_stmt = (
        select(User.id, User.role, User.is_active)
        .where(User.id == assignee_user_id)
        .limit(1)
    )
    user_row = (await db.execute(user_stmt)).first()
    if not user_row:
        return None, "assignee_not_found"
    if user_row.is_active != 1:
        return None, "assignee_inactive"
    if user_row.role not in {"support_agent", "supervisor"}:
        return None, "assignee_role_invalid"

    assign_stmt = (
        update(Ticket)
        .where(Ticket.id == ticket_id)
        .values(assignee_id=assignee_user_id, status="assigned")
        .returning(
            Ticket.id,
            Ticket.title,
            Ticket.description,
            Ticket.category,
            Ticket.priority,
            Ticket.sentiment,
            Ticket.status,
            Ticket.assignee_id,
        )
    )
    assigned_row = (await db.execute(assign_stmt)).first()
    await db.commit()
    return assigned_row, None


async def mark_ticket_resolved_by_assignee(db: AsyncSession, ticket_id: int, assignee_user_id: int):
    ticket_stmt = (
        select(Ticket.id, Ticket.assignee_id, Ticket.status)
        .where(Ticket.id == ticket_id)
        .limit(1)
    )
    ticket_row = (await db.execute(ticket_stmt)).first()
    if not ticket_row:
        return None, "ticket_not_found"
    if ticket_row.assignee_id != assignee_user_id:
        return None, "not_assigned_to_user"
    if ticket_row.status == "closed":
        return None, "ticket_already_closed"

    resolve_stmt = (
        update(Ticket)
        .where(Ticket.id == ticket_id)
        .values(status="resolved")
        .returning(
            Ticket.id,
            Ticket.title,
            Ticket.description,
            Ticket.category,
            Ticket.priority,
            Ticket.sentiment,
            Ticket.status,
            Ticket.assignee_id,
        )
    )
    row = (await db.execute(resolve_stmt)).first()
    await db.commit()
    return row, None


async def close_ticket_by_admin(db: AsyncSession, ticket_id: int):
    ticket_stmt = (
        select(Ticket.id, Ticket.status)
        .where(Ticket.id == ticket_id)
        .limit(1)
    )
    ticket_row = (await db.execute(ticket_stmt)).first()
    if not ticket_row:
        return None, "ticket_not_found"
    if ticket_row.status != "resolved":
        return None, "ticket_not_resolved"

    close_stmt = (
        update(Ticket)
        .where(Ticket.id == ticket_id)
        .values(status="closed")
        .returning(
            Ticket.id,
            Ticket.title,
            Ticket.description,
            Ticket.category,
            Ticket.priority,
            Ticket.sentiment,
            Ticket.status,
            Ticket.assignee_id,
        )
    )
    row = (await db.execute(close_stmt)).first()
    await db.commit()
    return row, None


async def update_ticket_work_status_by_assignee(
    db: AsyncSession,
    ticket_id: int,
    assignee_user_id: int,
    new_status: str,
):
    if new_status not in {"in_review", "in_progress", "resolved"}:
        return None, "invalid_status"

    ticket_stmt = (
        select(Ticket.id, Ticket.assignee_id, Ticket.status)
        .where(Ticket.id == ticket_id)
        .limit(1)
    )
    ticket_row = (await db.execute(ticket_stmt)).first()
    if not ticket_row:
        return None, "ticket_not_found"
    if ticket_row.assignee_id != assignee_user_id:
        return None, "not_assigned_to_user"
    if ticket_row.status == "closed":
        return None, "ticket_already_closed"

    update_stmt = (
        update(Ticket)
        .where(Ticket.id == ticket_id)
        .values(status=new_status)
        .returning(
            Ticket.id,
            Ticket.title,
            Ticket.description,
            Ticket.category,
            Ticket.priority,
            Ticket.sentiment,
            Ticket.status,
            Ticket.assignee_id,
        )
    )
    row = (await db.execute(update_stmt)).first()
    await db.commit()
    return row, None


async def add_ticket_conversation_message(
    db: AsyncSession,
    ticket_id: int,
    sender_user_id: int,
    sender_role: str,
    message_type: str,
    message: str,
):
    ticket_exists_stmt = select(Ticket.id).where(Ticket.id == ticket_id).limit(1)
    ticket_exists = (await db.execute(ticket_exists_stmt)).first()
    if not ticket_exists:
        return None, "ticket_not_found"

    convo = TicketConversation(
        ticket_id=ticket_id,
        sender_user_id=sender_user_id,
        sender_role=sender_role,
        message_type=message_type,
        message=message.strip(),
    )
    db.add(convo)
    await db.commit()
    await db.refresh(convo)
    return convo, None


async def list_ticket_conversations(db: AsyncSession, ticket_id: int, limit: int = 200):
    ticket_exists_stmt = select(Ticket.id).where(Ticket.id == ticket_id).limit(1)
    ticket_exists = (await db.execute(ticket_exists_stmt)).first()
    if not ticket_exists:
        return None, "ticket_not_found"

    stmt = (
        select(
            TicketConversation.id,
            TicketConversation.ticket_id,
            TicketConversation.sender_user_id,
            TicketConversation.sender_role,
            TicketConversation.message_type,
            TicketConversation.message,
            TicketConversation.created_at,
        )
        .where(TicketConversation.ticket_id == ticket_id)
        .order_by(TicketConversation.created_at.asc(), TicketConversation.id.asc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    return rows, None


async def get_employee_workload(db: AsyncSession, limit: int = 50):
    # Active ticket counts per employee role for admin insights.
    workload_stmt = (
        select(Ticket.assignee_id, func.count(Ticket.id))
        .where(Ticket.assignee_id.is_not(None), Ticket.status.in_(["open", "assigned", "in_progress"]))
        .group_by(Ticket.assignee_id)
    )
    counts = {row[0]: row[1] for row in (await db.execute(workload_stmt)).all()}

    users_stmt = (
        select(User.id, User.full_name, User.email, User.role, User.is_active)
        .where(User.role.in_(["support_agent", "supervisor"]), User.is_active == 1)
        .limit(limit)
    )
    users = (await db.execute(users_stmt)).all()
    return [
        {
            "user_id": row.id,
            "full_name": row.full_name,
            "email": row.email,
            "role": row.role,
            "active_tickets": int(counts.get(row.id, 0)),
        }
        for row in users
    ]


async def smart_assign_ticket(db: AsyncSession, ticket_id: int):
    ticket_stmt = (
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
    ticket = (await db.execute(ticket_stmt)).first()
    if not ticket:
        return None, "ticket_not_found"

    users_stmt = (
        select(User.id, User.role, User.is_active)
        .where(User.role.in_(["support_agent", "supervisor"]), User.is_active == 1)
        .limit(500)
    )
    candidates = (await db.execute(users_stmt)).all()
    if not candidates:
        return None, "no_active_employee"

    workload_stmt = (
        select(Ticket.assignee_id, func.count(Ticket.id))
        .where(Ticket.assignee_id.is_not(None), Ticket.status.in_(["open", "assigned", "in_progress"]))
        .group_by(Ticket.assignee_id)
    )
    load_counts = {row[0]: row[1] for row in (await db.execute(workload_stmt)).all()}

    heap: list[tuple[int, int]] = []
    for user in candidates:
        heapq.heappush(heap, (int(load_counts.get(user.id, 0)), int(user.id)))

    _load, selected_user_id = heapq.heappop(heap)
    assigned_row, error = await assign_ticket_to_user(db, ticket_id=ticket_id, assignee_user_id=selected_user_id)
    return assigned_row, error
