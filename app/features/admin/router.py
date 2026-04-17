from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.features.users.deps import require_admin
from app.features.users.models import User
from app.features.users.schemas import UserResponse
from app.features.users.service import list_all_users
from app.features.tickets.models import Ticket
from app.features.tickets.schemas import TicketResponse
from app.features.tickets.service import list_all_tickets


router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/users", response_model=list[UserResponse])
async def admin_list_users(
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    rows = await list_all_users(db, limit=limit)
    return [
        UserResponse(
            id=row.id,
            tenant_id=row.tenant_id,
            full_name=row.full_name,
            email=row.email,
            role=row.role,
            is_active=row.is_active,
        )
        for row in rows
    ]


@router.get("/tickets", response_model=list[TicketResponse])
async def admin_list_tickets(
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    rows = await list_all_tickets(db, limit=limit)
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


@router.get("/stats")
async def admin_stats(
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    users_total = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    tickets_total = (await db.execute(select(func.count()).select_from(Ticket))).scalar_one()
    open_tickets = (
        await db.execute(select(func.count()).select_from(Ticket).where(Ticket.status.in_(["open", "assigned"])))
    ).scalar_one()
    resolved_tickets = (
        await db.execute(select(func.count()).select_from(Ticket).where(Ticket.status.in_(["resolved", "closed"])))
    ).scalar_one()

    return {
        "users_total": users_total,
        "tickets_total": tickets_total,
        "open_or_assigned_tickets": open_tickets,
        "resolved_or_closed_tickets": resolved_tickets,
    }
