from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.features.users.deps import require_admin
from app.features.users.models import User
from app.features.users.schemas import UserAdminUpdate, UserResponse, UserRoleUpdate, UserStatusUpdate
from app.features.users.service import (
    delete_user_by_admin,
    list_all_users,
    update_user_by_admin,
    update_user_role,
    update_user_status,
)
from app.features.tickets.models import Ticket
from app.features.tickets.schemas import (
    TicketAssignRequest,
    TicketResponse,
    TicketRoutingSuggestionResponse,
    ticket_response_from_row,
)
from app.features.tickets.service import (
    assign_ticket_to_user,
    build_admin_ticket_routing_suggestion,
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
            department=row.department or "",
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
    return [ticket_response_from_row(row) for row in rows]


@router.get("/tickets/{ticket_id}/routing-suggestion", response_model=TicketRoutingSuggestionResponse)
async def admin_ticket_routing_suggestion(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    data, error = await build_admin_ticket_routing_suggestion(db, ticket_id=ticket_id)
    if error == "ticket_not_found":
        raise HTTPException(status_code=404, detail="Ticket not found")
    if not data:
        raise HTTPException(status_code=500, detail="Unable to build routing suggestion")
    return data


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

    return ticket_response_from_row(row)


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
    if error == "assignee_required_for_close":
        raise HTTPException(
            status_code=400,
            detail="Ticket must be resolved by an assigned employee before admin can close it.",
        )
    if error:
        raise HTTPException(status_code=500, detail="Unable to close ticket")

    return ticket_response_from_row(row)


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

    return ticket_response_from_row(row)


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
        department=user.department or "",
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
        department=user.department or "",
        is_active=user.is_active,
    )


@router.patch("/users/{user_id}", response_model=UserResponse)
async def admin_update_user(
    user_id: int,
    payload: UserAdminUpdate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    user, error = await update_user_by_admin(
        db,
        user_id,
        full_name=data.get("full_name"),
        email=data.get("email"),
        role=data.get("role"),
        department=data.get("department"),
        is_active=data.get("is_active"),
    )
    if error == "not_found":
        raise HTTPException(status_code=404, detail="User not found")
    if error == "email_taken":
        raise HTTPException(status_code=400, detail="Email already in use")
    if not user:
        raise HTTPException(status_code=500, detail="Unable to update user")
    return UserResponse(
        id=user.id,
        tenant_id=user.tenant_id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        department=user.department or "",
        is_active=user.is_active,
    )


@router.delete("/users/{user_id}", status_code=204)
async def admin_delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin),
):
    error = await delete_user_by_admin(db, user_id=user_id, admin_user_id=admin.id)
    if error == "not_found":
        raise HTTPException(status_code=404, detail="User not found")
    if error == "cannot_delete_self":
        raise HTTPException(status_code=400, detail="You cannot delete your own account")
    return None


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
