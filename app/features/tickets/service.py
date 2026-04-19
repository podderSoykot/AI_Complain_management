import asyncio
import heapq
import mimetypes
import re
import uuid
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from app.core.config import get_settings
from app.features.tickets.models import TicketAttachment
from app.features.tickets.models import TicketConversation
from app.features.agents.models import Agent
from app.features.tickets.models import Ticket
from app.features.tickets.schemas import (
    TicketAttachmentPublic,
    TicketRoutingCandidate,
    TicketRoutingSuggestionResponse,
)
from app.features.users.models import User


settings = get_settings()
THREAD_POOL = ThreadPoolExecutor(max_workers=settings.max_workers_thread)
PROCESS_POOL = ProcessPoolExecutor(max_workers=settings.max_workers_process)

ALLOWED_ATTACHMENT_SUFFIXES = frozenset(
    {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".txt", ".csv", ".doc", ".docx", ".xls", ".xlsx"}
)


def _sanitize_original_filename(name: str) -> str:
    base = Path(name or "document").name
    base = re.sub(r"[^\w.\- ]", "_", base).strip() or "document"
    return base[:200]


def _suffix_allowed(original_name: str, content_type: str | None = None) -> str:
    suf = Path(original_name).suffix.lower()
    if suf in ALLOWED_ATTACHMENT_SUFFIXES:
        return suf
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct:
        guessed = mimetypes.guess_extension(ct, strict=False)
        if guessed == ".jpe":
            guessed = ".jpeg"
        if guessed and guessed.lower() in ALLOWED_ATTACHMENT_SUFFIXES:
            return guessed.lower()
    guessed2 = mimetypes.guess_extension(mimetypes.guess_type(original_name)[0] or "") or ""
    if guessed2.lower() in ALLOWED_ATTACHMENT_SUFFIXES:
        return guessed2.lower()
    raise ValueError(f"File type not allowed (use a known extension such as .pdf or .png): {suf or '(no extension)'}")


async def persist_ticket_attachments(
    db: AsyncSession,
    ticket_id: int,
    file_payloads: list[tuple[str, str, bytes]],
) -> None:
    if not file_payloads:
        return
    settings = get_settings()
    upload_root = Path(settings.ticket_upload_dir)
    upload_root.mkdir(parents=True, exist_ok=True)
    max_each = settings.ticket_max_upload_bytes
    for original_name, content_type, data in file_payloads:
        if len(data) > max_each:
            raise ValueError(f"File exceeds maximum size ({max_each // (1024 * 1024)} MB)")
        safe_name = _sanitize_original_filename(original_name)
        suf = _suffix_allowed(safe_name, content_type)
        stored = f"{uuid.uuid4().hex}{suf}"
        path = upload_root / stored
        path.write_bytes(data)
        ct = content_type or mimetypes.guess_type(safe_name)[0] or "application/octet-stream"
        row = TicketAttachment(
            ticket_id=ticket_id,
            original_filename=safe_name,
            stored_filename=stored,
            content_type=ct[:120],
            size_bytes=len(data),
        )
        db.add(row)
    await db.commit()


def user_can_view_ticket_files(user: User, ticket: Ticket) -> bool:
    if user.role == "admin":
        return True
    if user.role in {"support_agent", "supervisor"}:
        return True
    if user.role == "customer" and ticket.reporter_id is not None and ticket.reporter_id == user.id:
        return True
    return False


async def list_attachment_rows(db: AsyncSession, ticket_id: int):
    stmt = (
        select(
            TicketAttachment.id,
            TicketAttachment.original_filename,
            TicketAttachment.content_type,
            TicketAttachment.size_bytes,
            TicketAttachment.created_at,
        )
        .where(TicketAttachment.ticket_id == ticket_id)
        .order_by(TicketAttachment.id.asc())
    )
    return (await db.execute(stmt)).all()


async def get_attachment_row(db: AsyncSession, ticket_id: int, attachment_id: int):
    stmt = (
        select(
            TicketAttachment.id,
            TicketAttachment.ticket_id,
            TicketAttachment.original_filename,
            TicketAttachment.stored_filename,
            TicketAttachment.content_type,
            TicketAttachment.size_bytes,
        )
        .where(TicketAttachment.id == attachment_id, TicketAttachment.ticket_id == ticket_id)
        .limit(1)
    )
    return (await db.execute(stmt)).first()


def attachment_disk_path(stored_filename: str) -> Path:
    return Path(get_settings().ticket_upload_dir) / stored_filename


def classify_text(text: str) -> str:
    """Lightweight NLP: keyword / phrase signals (English + common Bangla complaints)."""
    text_cf = text.casefold()
    # Billing / payment (EN + BN)
    billing_kw = (
        "payment",
        "billing",
        "deducted",
        "invoice",
        "refund",
        "charged",
        "money was",
        "card",
        "double charge",
        "টাকা",
        "পেমেন্ট",
        "বিল",
        "কেটে",
        "টাকা কেটে",
        "বকেয়া",
    )
    if any(k in text_cf for k in billing_kw):
        return "billing"
    # Account / access
    account_kw = (
        "login",
        "password",
        "account",
        "otp",
        "sign in",
        "signin",
        "locked out",
        "cannot access",
        "লগইন",
        "পাসওয়ার্ড",
        "অ্যাকাউন্ট",
    )
    if any(k in text_cf for k in account_kw):
        return "account"
    # Technical / product failure
    tech_kw = (
        "error",
        "bug",
        "crash",
        "not working",
        "slow",
        "timeout",
        "502",
        "503",
        "broken",
        "কাজ করছে না",
        "এরর",
    )
    if any(k in text_cf for k in tech_kw):
        return "technical"
    return "complaint"


ROUTING_ADMIN_GUIDANCE: dict[str, str] = {
    "billing": (
        "Complaint reads like billing or payment. Prefer an employee whose department "
        "mentions Billing, Finance, Payments, or Invoices so FAQs and refunds are handled fastest."
    ),
    "account": (
        "Complaint reads like login, password, or account access. Prefer Account, Access, "
        "Identity, or Customer Onboarding departments."
    ),
    "technical": (
        "Complaint reads like bugs, errors, or the product not working. Prefer Technical, IT, "
        "Engineering, or Tier-2 support departments."
    ),
    "complaint": (
        "General service complaint. Prefer General Support, Customer Care, or Operations; "
        "among similar matches, pick the lightest workload."
    ),
}

# Map detected category → substrings that may appear in User.department (case-insensitive).
CATEGORY_DEPT_HINTS: dict[str, tuple[str, ...]] = {
    "billing": (
        "bill",
        "payment",
        "finance",
        "invoice",
        "accounting",
        "revenue",
        "cash",
        "refund",
        "card",
    ),
    "account": (
        "account",
        "access",
        "login",
        "identity",
        "profile",
        "onboard",
        "credential",
        "customer success",
        "সাপোর্ট",
    ),
    "technical": (
        "technical",
        "engineering",
        "software",
        "network",
        "server",
        "devops",
        "developer",
        "tier 2",
        "tier2",
        "it support",
        "product",
    ),
    "complaint": (
        "general",
        "customer",
        "helpdesk",
        "front",
        "operations",
        "service",
        "support",
        "care",
    ),
}


def department_match_score(category: str, department: str) -> int:
    d = (department or "").casefold()
    if not d.strip():
        return 0
    hints = CATEGORY_DEPT_HINTS.get(category, CATEGORY_DEPT_HINTS["complaint"])
    score = sum(1 for h in hints if h.casefold() in d)
    if category.casefold() in d:
        score += 2
    return score


def _candidate_rationale(nlp_category: str, department: str, match_score: int) -> str:
    if match_score > 0:
        return (
            f'Department "{department}" matches the {nlp_category} theme of this complaint '
            f"(match score {match_score}). Assign here for the fastest aligned resolution."
        )
    return (
        "Department name did not strongly match this complaint theme; "
        "still listed so you can compare workload and pick manually."
    )


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


async def create_ticket_enriched(
    db: AsyncSession,
    title: str,
    description: str,
    reporter_id: int | None = None,
    file_payloads: list[tuple[str, str, bytes]] | None = None,
) -> Ticket:
    ticket = Ticket(title=title, description=description, reporter_id=reporter_id)
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
    if file_payloads:
        await persist_ticket_attachments(db, ticket.id, file_payloads)
    return ticket


async def get_ticket_by_id(db: AsyncSession, ticket_id: int) -> Ticket | None:
    stmt = select(Ticket).where(Ticket.id == ticket_id).limit(1)
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_latest_active_ticket_for_reporter(db: AsyncSession, reporter_id: int) -> Ticket | None:
    """Newest non-closed ticket this user reported (for one-click agent without typing ID)."""
    stmt = (
        select(Ticket)
        .where(Ticket.reporter_id == reporter_id, Ticket.status != "closed")
        .order_by(Ticket.id.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_latest_global_ticket_for_admin_agent(db: AsyncSession) -> Ticket | None:
    """Newest non-closed ticket overall (admin agent without selecting an ID)."""
    stmt = (
        select(Ticket)
        .where(Ticket.status != "closed")
        .order_by(Ticket.id.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def count_attachments(db: AsyncSession, ticket_id: int) -> int:
    stmt = select(func.count()).select_from(TicketAttachment).where(TicketAttachment.ticket_id == ticket_id)
    return int((await db.execute(stmt)).scalar_one() or 0)


async def list_attachments_public(db: AsyncSession, ticket_id: int) -> list[TicketAttachmentPublic]:
    rows = await list_attachment_rows(db, ticket_id)
    return [
        TicketAttachmentPublic(
            id=r.id,
            original_filename=r.original_filename,
            content_type=r.content_type,
            size_bytes=r.size_bytes,
            created_at=r.created_at,
        )
        for r in rows
    ]


async def list_all_tickets(db: AsyncSession, limit: int = 100):
    assignee_user = aliased(User)
    attachment_count_sq = (
        select(func.count())
        .select_from(TicketAttachment)
        .where(TicketAttachment.ticket_id == Ticket.id)
        .scalar_subquery()
    )
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
            Ticket.reporter_id,
            attachment_count_sq.label("attachment_count"),
            assignee_user.full_name.label("assignee_full_name"),
            assignee_user.department.label("assignee_department"),
        )
        .outerjoin(assignee_user, Ticket.assignee_id == assignee_user.id)
        .order_by(Ticket.id.desc())
        .limit(limit)
    )
    return (await db.execute(stmt)).all()


async def list_assigned_tickets_for_user(db: AsyncSession, assignee_user_id: int, limit: int = 100):
    attachment_count_sq = (
        select(func.count())
        .select_from(TicketAttachment)
        .where(TicketAttachment.ticket_id == Ticket.id)
        .scalar_subquery()
    )
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
            Ticket.reporter_id,
            attachment_count_sq.label("attachment_count"),
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
            Ticket.reporter_id,
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
            Ticket.reporter_id,
        )
    )
    row = (await db.execute(resolve_stmt)).first()
    await db.commit()
    return row, None


async def admin_mark_ticket_resolved(db: AsyncSession, ticket_id: int):
    """
    Admin-only: set ticket status to resolved (e.g. AI-assisted closure path).
    Returns (ticket_row_or_none, error_code, did_transition) where did_transition is True
    when status changed from a non-resolved state to resolved.
    """
    ticket_stmt = (
        select(Ticket.id, Ticket.status)
        .where(Ticket.id == ticket_id)
        .limit(1)
    )
    ticket_row = (await db.execute(ticket_stmt)).first()
    if not ticket_row:
        return None, "ticket_not_found", False
    if ticket_row.status == "closed":
        return None, "ticket_closed", False
    if ticket_row.status == "resolved":
        row = await get_ticket_by_id(db, ticket_id)
        return row, None, False

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
            Ticket.reporter_id,
        )
    )
    row = (await db.execute(resolve_stmt)).first()
    await db.commit()
    return row, None, True


async def close_ticket_by_admin(db: AsyncSession, ticket_id: int):
    ticket_stmt = (
        select(Ticket.id, Ticket.status, Ticket.assignee_id)
        .where(Ticket.id == ticket_id)
        .limit(1)
    )
    ticket_row = (await db.execute(ticket_stmt)).first()
    if not ticket_row:
        return None, "ticket_not_found"
    if ticket_row.status != "resolved":
        return None, "ticket_not_resolved"
    if ticket_row.assignee_id is None:
        return None, "assignee_required_for_close"

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
            Ticket.reporter_id,
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
    if ticket_row.assignee_id is None:
        return None, "not_assigned_to_user"
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
            Ticket.reporter_id,
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
        select(User.id, User.full_name, User.email, User.role, User.department, User.is_active)
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
            "department": row.department or "",
            "active_tickets": int(counts.get(row.id, 0)),
        }
        for row in users
    ]


async def build_admin_ticket_routing_suggestion(
    db: AsyncSession, ticket_id: int,
) -> tuple[TicketRoutingSuggestionResponse | None, str | None]:
    """NLP-style complaint theme + rank employees by department fit and active workload."""
    ticket = await get_ticket_by_id(db, ticket_id)
    if not ticket:
        return None, "ticket_not_found"

    text = f"{ticket.title} {ticket.description}"
    nlp_category = classify_text(text)
    guidance = ROUTING_ADMIN_GUIDANCE.get(nlp_category, ROUTING_ADMIN_GUIDANCE["complaint"])

    users_stmt = (
        select(User.id, User.full_name, User.email, User.role, User.department)
        .where(User.role.in_(["support_agent", "supervisor"]), User.is_active == 1)
        .limit(500)
    )
    rows = (await db.execute(users_stmt)).all()

    workload_stmt = (
        select(Ticket.assignee_id, func.count(Ticket.id))
        .where(Ticket.assignee_id.is_not(None), Ticket.status.in_(["open", "assigned", "in_progress"]))
        .group_by(Ticket.assignee_id)
    )
    load_counts = {row[0]: row[1] for row in (await db.execute(workload_stmt)).all()}

    if not rows:
        return (
            TicketRoutingSuggestionResponse(
                ticket_id=ticket_id,
                nlp_category=nlp_category,
                admin_guidance=guidance,
                candidates=[],
                recommended_user_id=None,
            ),
            None,
        )

    candidates: list[TicketRoutingCandidate] = []
    for row in rows:
        dept = row.department or ""
        ms = department_match_score(nlp_category, dept)
        load = int(load_counts.get(row.id, 0))
        candidates.append(
            TicketRoutingCandidate(
                user_id=row.id,
                full_name=row.full_name or "",
                email=row.email or "",
                role=row.role,
                department=dept,
                department_match_score=ms,
                active_tickets=load,
                rationale=_candidate_rationale(nlp_category, dept, ms),
            )
        )

    candidates.sort(key=lambda c: (-c.department_match_score, c.active_tickets, c.user_id))

    best_ms = candidates[0].department_match_score
    pool = [c for c in candidates if c.department_match_score == best_ms] if best_ms > 0 else list(candidates)
    recommended = min(pool, key=lambda c: (c.active_tickets, c.user_id)).user_id

    return (
        TicketRoutingSuggestionResponse(
            ticket_id=ticket_id,
            nlp_category=nlp_category,
            admin_guidance=guidance,
            candidates=candidates,
            recommended_user_id=recommended,
        ),
        None,
    )


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

    text = f"{ticket.title} {ticket.description}"
    nlp_category = classify_text(text)

    users_stmt = (
        select(User.id, User.role, User.is_active, User.department)
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

    scored = [
        (int(u.id), department_match_score(nlp_category, (u.department or "")))
        for u in candidates
    ]
    max_ms = max((s[1] for s in scored), default=0)
    pool_ids = [uid for uid, ms in scored if ms == max_ms] if max_ms > 0 else [uid for uid, _ in scored]
    selected_user_id = min(pool_ids, key=lambda uid: (int(load_counts.get(uid, 0)), uid))

    assigned_row, error = await assign_ticket_to_user(db, ticket_id=ticket_id, assignee_user_id=selected_user_id)
    return assigned_row, error
