from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.core.perf import timed_endpoint
from app.core.config import get_settings
from app.features.tickets.schemas import (
    TicketConversationCreate,
    TicketConversationResponse,
    TicketResponse,
    TicketStatusUpdateRequest,
    ticket_response_from_row,
)
from app.features.tickets.service import (
    add_ticket_conversation_message,
    attachment_disk_path,
    count_attachments,
    create_ticket_enriched,
    get_attachment_row,
    get_ticket_by_id,
    list_assigned_tickets_for_user,
    list_attachments_public,
    list_ticket_conversations,
    update_ticket_work_status_by_assignee,
    user_can_view_ticket_files,
)
from app.features.users.deps import get_current_user, require_support_or_supervisor


router = APIRouter(prefix="/api/v1", tags=["tickets"])


@router.post("/tickets", response_model=TicketResponse)
async def create_ticket(
    title: str = Form(..., min_length=3, max_length=160),
    description: str = Form(..., min_length=10, max_length=4000),
    files: list[UploadFile] | None = File(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    settings = get_settings()
    uploads = files or []
    if len(uploads) > settings.ticket_max_files_per_ticket:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files (max {settings.ticket_max_files_per_ticket})",
        )
    file_payloads: list[tuple[str, str, bytes]] = []
    for uf in uploads:
        if not uf.filename:
            continue
        raw = await uf.read()
        if len(raw) > settings.ticket_max_upload_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"File {uf.filename!r} exceeds max size ({settings.ticket_max_upload_bytes // (1024 * 1024)} MB)",
            )
        ct = uf.content_type or "application/octet-stream"
        file_payloads.append((uf.filename, ct, raw))

    try:
        ticket = await create_ticket_enriched(
            db,
            title.strip(),
            description.strip(),
            reporter_id=current_user.id,
            file_payloads=file_payloads or None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    n = await count_attachments(db, ticket.id)
    atts = await list_attachments_public(db, ticket.id) if n else []
    return ticket_response_from_row(ticket, attachments=atts)


@router.get("/tickets/assigned/me", response_model=list[TicketResponse])
async def get_my_assigned_tickets(
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_support_or_supervisor),
):
    rows = await list_assigned_tickets_for_user(db, assignee_user_id=current_user.id, limit=limit)
    return [ticket_response_from_row(r) for r in rows]


@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ticket = await get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if not user_can_view_ticket_files(current_user, ticket):
        raise HTTPException(status_code=403, detail="Not allowed to view this ticket")
    n = await count_attachments(db, ticket_id)
    atts = await list_attachments_public(db, ticket_id) if n else []
    return ticket_response_from_row(ticket, attachments=atts)


@router.get("/tickets/{ticket_id}/attachments/{attachment_id}/download")
async def download_ticket_attachment(
    ticket_id: int,
    attachment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ticket = await get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if not user_can_view_ticket_files(current_user, ticket):
        raise HTTPException(status_code=403, detail="Not allowed to download this file")

    row = await get_attachment_row(db, ticket_id, attachment_id)
    if not row:
        raise HTTPException(status_code=404, detail="Attachment not found")

    path = attachment_disk_path(row.stored_filename)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File missing on server")

    return FileResponse(
        path=str(path),
        media_type=row.content_type or "application/octet-stream",
        filename=row.original_filename,
        content_disposition_type="inline",
    )


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

    ticket = await get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    n = await count_attachments(db, ticket_id)
    atts = await list_attachments_public(db, ticket_id) if n else []
    return ticket_response_from_row(ticket, attachments=atts)


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
