"""LLM-backed support agent: admin copilot + customer-facing chat."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.features.llm import assert_llm_configured, chat_completion, safe_parse_json_object
from app.features.tickets.models import Ticket
from app.features.tickets.service import (
    add_ticket_conversation_message,
    admin_mark_ticket_resolved,
    get_latest_active_ticket_for_reporter,
    get_latest_global_ticket_for_admin_agent,
    get_ticket_by_id,
    list_ticket_conversations,
)

AI_SENDER_USER_ID = 0

# One-click "Work with agent" — full autonomous prompt (admin may mark resolved via JSON path).
ADMIN_ONE_CLICK_AGENT_MESSAGE = (
    "The admin chose **Work with agent** (single-click autonomous mode). "
    "Analyze the ticket and the full conversation thread: summarize the issue, risks, and concrete next steps. "
    "If the matter is clearly complete or already adequately handled from an operations perspective, set mark_resolved true; "
    "otherwise false and explain what staff should still do."
)

CUSTOMER_ONE_CLICK_AGENT_MESSAGE = (
    "[Work with agent] The customer used one-click assistance. "
    "Review the ticket and entire thread, then give a clear, helpful reply and practical next steps."
)


def _ticket_block(ticket: Ticket) -> str:
    return (
        f"Ticket #{ticket.id}\n"
        f"Title: {ticket.title}\n"
        f"Status: {ticket.status}\n"
        f"Category: {ticket.category}\n"
        f"Priority: {ticket.priority}\n"
        f"Sentiment: {ticket.sentiment}\n"
        f"Assignee user id: {ticket.assignee_id}\n"
        f"Reporter user id: {ticket.reporter_id}\n"
        f"Description:\n{ticket.description}\n"
    )


def _history_block(rows: list[Any]) -> str:
    lines: list[str] = []
    for r in rows[-35:]:
        role = r.sender_role or "user"
        mt = r.message_type or "note"
        lines.append(f"[{mt}] {role} (#{r.sender_user_id}): {r.message}")
    return "\n".join(lines) if lines else "(no prior messages)"


async def _ensure_ai_config():
    settings = get_settings()
    assert_llm_configured(settings)
    return settings


async def run_admin_ticket_ai(
    db: AsyncSession,
    *,
    ticket_id: int,
    admin_message: str,
    apply_resolution: bool,
) -> dict[str, Any]:
    settings = await _ensure_ai_config()
    ticket = await get_ticket_by_id(db, ticket_id)
    if not ticket:
        return {"error": "ticket_not_found"}

    rows, err = await list_ticket_conversations(db, ticket_id, limit=200)
    if err:
        return {"error": "conversation_load_failed"}

    sys = (
        "You are an expert support operations copilot helping an ADMIN manage complaint tickets.\n"
        "Be concise, professional, and actionable. Reference ticket facts only from the context.\n"
        "You may suggest next steps (assign, ask customer for info, document request, escalate).\n"
        "Never invent policy; if unsure, say what you need to know.\n"
        "Do not claim you executed backend actions unless told the system already applied them."
    )

    user_ctx = (
        _ticket_block(ticket)
        + "\nRecent conversation (oldest to newest):\n"
        + _history_block(list(rows or []))
        + f"\n\nAdmin question or instruction:\n{admin_message.strip()}\n"
    )

    initial_status = ticket.status

    if apply_resolution:
        user_ctx += (
            "\n\nThe admin asked to APPLY A RESOLUTION DECISION.\n"
            "Respond with a single JSON object ONLY (no markdown) with keys:\n"
            '  "assistant_reply": string (what you tell the admin),\n'
            '  "mark_resolved": boolean (true only if the issue is clearly handled or no further work is needed),\n'
            '  "resolution_summary": string (short note suitable for the ticket thread; empty if not resolving).\n'
            "Set mark_resolved true only when it is reasonable to mark the ticket resolved from an admin perspective."
        )
        raw = await chat_completion(
            messages=[
                {"role": "system", "content": sys},
                {"role": "user", "content": user_ctx},
            ],
            temperature=0.2,
            json_mode=True,
            settings=settings,
        )
        parsed = safe_parse_json_object(raw) or {}
        reply = str(parsed.get("assistant_reply") or "").strip() or raw
        mark = bool(parsed.get("mark_resolved"))
        summary = str(parsed.get("resolution_summary") or "").strip()

        resolution_applied = False
        if mark:
            if initial_status == "closed":
                pass
            elif initial_status == "resolved":
                pass
            else:
                _row2, res_err, did_transition = await admin_mark_ticket_resolved(db, ticket_id)
                resolution_applied = res_err is None and bool(did_transition)

        body = reply
        if summary and summary not in body:
            body += f"\n\nResolution note: {summary}"
        if mark:
            if initial_status == "closed":
                body += "\n\n— Ticket already **closed**; no status change."
            elif initial_status == "resolved":
                body += "\n\n— Ticket was already **resolved**; thread updated only."
            elif resolution_applied:
                body += "\n\n— Ticket status set to **resolved** (admin AI)."
            else:
                body += "\n\n— AI suggested resolve but status was not changed; please review manually."

        await add_ticket_conversation_message(
            db,
            ticket_id=ticket_id,
            sender_user_id=AI_SENDER_USER_ID,
            sender_role="assistant",
            message_type="ai_admin",
            message=body[:4000],
        )

        return {
            "reply": reply,
            "resolution_applied": resolution_applied,
            "raw_json": parsed if parsed else None,
        }

    raw = await chat_completion(
        messages=[
            {"role": "system", "content": sys},
            {"role": "user", "content": user_ctx},
        ],
        temperature=0.35,
        json_mode=False,
        settings=settings,
    )
    await add_ticket_conversation_message(
        db,
        ticket_id=ticket_id,
        sender_user_id=AI_SENDER_USER_ID,
        sender_role="assistant",
        message_type="ai_admin",
        message=raw[:4000],
    )
    return {"reply": raw, "resolution_applied": False}


async def run_admin_agent_one_click(
    db: AsyncSession,
    *,
    ticket_id: int,
) -> dict[str, Any]:
    """Admin: one button — analyze thread, reply on ticket, may set status to resolved."""
    return await run_admin_ticket_ai(
        db,
        ticket_id=ticket_id,
        admin_message=ADMIN_ONE_CLICK_AGENT_MESSAGE,
        apply_resolution=True,
    )


async def run_customer_agent_one_click(
    db: AsyncSession,
    *,
    ticket_id: int,
    customer_user_id: int,
) -> dict[str, Any]:
    """Customer: one button — agent reads ticket + thread and posts a full reply."""
    return await run_customer_ticket_ai(
        db,
        ticket_id=ticket_id,
        customer_user_id=customer_user_id,
        customer_message=CUSTOMER_ONE_CLICK_AGENT_MESSAGE,
    )


async def run_customer_ticket_ai(
    db: AsyncSession,
    *,
    ticket_id: int,
    customer_user_id: int,
    customer_message: str,
) -> dict[str, Any]:
    settings = await _ensure_ai_config()
    ticket = await get_ticket_by_id(db, ticket_id)
    if not ticket:
        return {"error": "ticket_not_found"}
    if ticket.reporter_id is None or ticket.reporter_id != customer_user_id:
        return {"error": "not_reporter"}
    if ticket.status == "closed":
        return {"error": "ticket_closed"}

    await add_ticket_conversation_message(
        db,
        ticket_id=ticket_id,
        sender_user_id=customer_user_id,
        sender_role="customer",
        message_type="user_reply",
        message=customer_message.strip(),
    )

    rows, err = await list_ticket_conversations(db, ticket_id, limit=200)
    if err:
        return {"error": "conversation_load_failed"}

    sys = (
        "You are a helpful customer-support AI assistant chatting with the CUSTOMER who opened this ticket.\n"
        "Be polite, clear, and concise. Acknowledge their concern.\n"
        "If you need human staff, say a human agent will review the thread.\n"
        "Do not promise refunds or legal outcomes unless the ticket text clearly states they were approved.\n"
        "Never ask for passwords or full payment card numbers."
    )

    user_ctx = (
        _ticket_block(ticket)
        + "\nConversation including the customer's latest message:\n"
        + _history_block(list(rows or []))
    )

    raw = await chat_completion(
        messages=[
            {"role": "system", "content": sys},
            {"role": "user", "content": user_ctx},
        ],
        temperature=0.45,
        json_mode=False,
        settings=settings,
    )

    await add_ticket_conversation_message(
        db,
        ticket_id=ticket_id,
        sender_user_id=AI_SENDER_USER_ID,
        sender_role="assistant",
        message_type="ai_customer",
        message=raw[:4000],
    )
    return {"reply": raw}


async def run_customer_agent_auto_ticket(
    db: AsyncSession,
    *,
    customer_user_id: int,
) -> dict[str, Any]:
    """Pick latest non-closed ticket for this reporter, then one-click agent."""
    ticket = await get_latest_active_ticket_for_reporter(db, customer_user_id)
    if not ticket:
        return {"error": "no_active_ticket"}
    out = await run_customer_agent_one_click(db, ticket_id=ticket.id, customer_user_id=customer_user_id)
    if out.get("error"):
        return out
    out["ticket_id"] = ticket.id
    return out


async def run_admin_agent_auto_ticket(db: AsyncSession) -> dict[str, Any]:
    """Pick newest non-closed ticket globally, then admin one-click agent."""
    ticket = await get_latest_global_ticket_for_admin_agent(db)
    if not ticket:
        return {"error": "no_ticket"}
    out = await run_admin_agent_one_click(db, ticket_id=ticket.id)
    if out.get("error"):
        return out
    out["ticket_id"] = ticket.id
    return out
