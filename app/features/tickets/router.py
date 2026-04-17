from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.core.perf import timed_endpoint
from app.features.tickets.schemas import (
    TicketConversationCreate,
    TicketConversationResponse,
    TicketCreate,
    TicketResponse,
    TicketStatusUpdateRequest,
)
from app.features.tickets.service import (
    add_ticket_conversation_message,
    create_ticket_enriched,
    get_ticket_by_id,
    list_assigned_tickets_for_user,
    list_ticket_conversations,
    update_ticket_work_status_by_assignee,
)
from app.features.users.deps import get_current_user, require_support_or_supervisor


router = APIRouter(prefix="/api/v1", tags=["tickets"])


@router.post("/tickets", response_model=TicketResponse)
async def create_ticket(
    payload: TicketCreate,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    ticket = await create_ticket_enriched(db, payload.title, payload.description)
    return TicketResponse(
        id=ticket.id,
        title=ticket.title,
        description=ticket.description,
        category=ticket.category,
        priority=ticket.priority,
        sentiment=ticket.sentiment,
        status=ticket.status,
        assignee_id=ticket.assignee_id,
    )


@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: int, db: AsyncSession = Depends(get_db)):
    row = await get_ticket_by_id(db, ticket_id)
    if not row:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return TicketResponse(
        id=row.id,
        title=row.title,
        description=row.description,
        category=row.category,
        priority=row.priority,
        sentiment=row.sentiment,
        status=row.status,
        assignee_id=row.assignee_id,
    )


@router.get("/tickets/assigned/me", response_model=list[TicketResponse])
async def get_my_assigned_tickets(
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_support_or_supervisor),
):
    rows = await list_assigned_tickets_for_user(db, assignee_user_id=current_user.id, limit=limit)
    return [
        TicketResponse(
            id=row.id,
            title=row.title,
            description=row.description,
            category=row.category,
            priority=row.priority,
            sentiment=row.sentiment,
            status=row.status,
            assignee_id=row.assignee_id,
        )
        for row in rows
    ]


@router.patch("/tickets/{ticket_id}/work-status", response_model=TicketResponse)
async def assignee_update_ticket_work_status(
    ticket_id: int,
    payload: TicketStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_support_or_supervisor),
):
    row, error = await update_ticket_work_status_by_assignee(
        db,
        ticket_id=ticket_id,
        assignee_user_id=current_user.id,
        new_status=payload.status,
    )
    if error == "ticket_not_found":
        raise HTTPException(status_code=404, detail="Ticket not found")
    if error == "not_assigned_to_user":
        raise HTTPException(status_code=403, detail="Only assigned user can update this ticket")
    if error == "ticket_already_closed":
        raise HTTPException(status_code=400, detail="Ticket is already closed by admin")
    if error == "invalid_status":
        raise HTTPException(status_code=400, detail="Status must be in_review, in_progress or resolved")
    if error:
        raise HTTPException(status_code=500, detail="Unable to update ticket status")

    return TicketResponse(
        id=row.id,
        title=row.title,
        description=row.description,
        category=row.category,
        priority=row.priority,
        sentiment=row.sentiment,
        status=row.status,
        assignee_id=row.assignee_id,
    )


@router.post("/tickets/{ticket_id}/conversations", response_model=TicketConversationResponse)
async def post_ticket_conversation(
    ticket_id: int,
    payload: TicketConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    row, error = await add_ticket_conversation_message(
        db,
        ticket_id=ticket_id,
        sender_user_id=current_user.id,
        sender_role=current_user.role,
        message_type=payload.message_type,
        message=payload.message,
    )
    if error == "ticket_not_found":
        raise HTTPException(status_code=404, detail="Ticket not found")
    if error:
        raise HTTPException(status_code=500, detail="Unable to add conversation message")

    return TicketConversationResponse(
        id=row.id,
        ticket_id=row.ticket_id,
        sender_user_id=row.sender_user_id,
        sender_role=row.sender_role,
        message_type=row.message_type,
        message=row.message,
        created_at=row.created_at,
    )


@router.get("/tickets/{ticket_id}/conversations", response_model=list[TicketConversationResponse])
async def get_ticket_conversation(
    ticket_id: int,
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    rows, error = await list_ticket_conversations(db, ticket_id=ticket_id, limit=limit)
    if error == "ticket_not_found":
        raise HTTPException(status_code=404, detail="Ticket not found")
    if error:
        raise HTTPException(status_code=500, detail="Unable to fetch conversation")

    return [
        TicketConversationResponse(
            id=row.id,
            ticket_id=row.ticket_id,
            sender_user_id=row.sender_user_id,
            sender_role=row.sender_role,
            message_type=row.message_type,
            message=row.message,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.get("/health")
@timed_endpoint
async def health():
    return {"status": "ok"}
