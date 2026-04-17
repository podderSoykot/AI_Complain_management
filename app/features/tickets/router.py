from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.core.perf import timed_endpoint
from app.features.tickets.schemas import TicketCreate, TicketResponse
from app.features.tickets.service import create_ticket_enriched, get_ticket_by_id
from app.features.users.deps import get_current_user


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


@router.get("/health")
@timed_endpoint
async def health():
    return {"status": "ok"}
