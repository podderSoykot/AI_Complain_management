from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.features.users.deps import require_admin
from app.features.users.models import User
from app.features.users.schemas import UserResponse, UserRoleUpdate, UserStatusUpdate
from app.features.users.service import list_all_users, update_user_role, update_user_status
from app.features.tickets.models import Ticket
from app.features.tickets.schemas import TicketAssignRequest, TicketResponse
from app.features.tickets.service import (
    assign_ticket_to_user,
    close_ticket_by_admin,
    get_employee_workload,
    list_all_tickets,
    smart_assign_ticket,
)


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
        await db.execute(
            select(func.count()).select_from(Ticket).where(
                Ticket.status.in_(["open", "assigned", "in_review", "in_progress"])
            )
        )
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


@router.post("/tickets/{ticket_id}/assign", response_model=TicketResponse)
async def admin_assign_ticket(
    ticket_id: int,
    payload: TicketAssignRequest,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    row, error = await assign_ticket_to_user(db, ticket_id=ticket_id, assignee_user_id=payload.assignee_user_id)
    if error == "ticket_not_found":
        raise HTTPException(status_code=404, detail="Ticket not found")
    if error == "assignee_not_found":
        raise HTTPException(status_code=404, detail="Assignee user not found")
    if error == "assignee_inactive":
        raise HTTPException(status_code=400, detail="Assignee user is inactive")
    if error == "assignee_role_invalid":
        raise HTTPException(status_code=400, detail="Assignee role must be support_agent or supervisor")
    if not row:
        raise HTTPException(status_code=500, detail="Unable to assign ticket")

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


@router.patch("/tickets/{ticket_id}/close", response_model=TicketResponse)
async def admin_close_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    row, error = await close_ticket_by_admin(db, ticket_id=ticket_id)
    if error == "ticket_not_found":
        raise HTTPException(status_code=404, detail="Ticket not found")
    if error == "ticket_not_resolved":
        raise HTTPException(status_code=400, detail="Only resolved tickets can be closed")
    if error:
        raise HTTPException(status_code=500, detail="Unable to close ticket")

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


@router.post("/tickets/{ticket_id}/smart-assign", response_model=TicketResponse)
async def admin_smart_assign_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    row, error = await smart_assign_ticket(db, ticket_id=ticket_id)
    if error == "ticket_not_found":
        raise HTTPException(status_code=404, detail="Ticket not found")
    if error == "no_active_employee":
        raise HTTPException(status_code=400, detail="No active support employee available")
    if error:
        raise HTTPException(status_code=500, detail="Unable to smart-assign ticket")

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


@router.patch("/users/{user_id}/status", response_model=UserResponse)
async def admin_update_user_status(
    user_id: int,
    payload: UserStatusUpdate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    user = await update_user_status(db, user_id=user_id, is_active=payload.is_active)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        id=user.id,
        tenant_id=user.tenant_id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
    )


@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def admin_update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    user = await update_user_role(db, user_id=user_id, role=payload.role)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        id=user.id,
        tenant_id=user.tenant_id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
    )


@router.get("/insights/workload")
async def admin_workload_insights(
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    data = await get_employee_workload(db, limit=limit)
    sorted_data = sorted(data, key=lambda x: x["active_tickets"], reverse=True)
    return {
        "employees": sorted_data,
        "max_active_tickets": max((x["active_tickets"] for x in sorted_data), default=0),
        "min_active_tickets": min((x["active_tickets"] for x in sorted_data), default=0),
    }
