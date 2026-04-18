from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import create_access_token
from app.database.session import get_db
from app.features.users.schemas import TokenResponse, UserCreate, UserLogin, UserResponse
from app.features.users.service import authenticate_user, create_user, get_user_by_email, get_user_by_id, list_users


router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.post("", response_model=UserResponse)
async def create_user_endpoint(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await get_user_by_email(db, str(payload.email))
    if existing:
        raise HTTPException(status_code=409, detail="User email already exists")

    user = await create_user(db, payload)
    return UserResponse(
        id=user.id,
        tenant_id=user.tenant_id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        department=user.department or "",
        is_active=user.is_active,
    )


@router.post("/login", response_model=TokenResponse)
async def login_endpoint(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, str(payload.email), payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(subject=user.email)
    return TokenResponse(access_token=token)


@router.post("/login/admin", response_model=TokenResponse)
async def admin_login_endpoint(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, str(payload.email), payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin login only")
    token = create_access_token(subject=user.email)
    return TokenResponse(access_token=token)


@router.post("/login/employee", response_model=TokenResponse)
async def employee_login_endpoint(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, str(payload.email), payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user.role not in {"support_agent", "supervisor"}:
        raise HTTPException(status_code=403, detail="Employee login allowed for support_agent/supervisor")
    token = create_access_token(subject=user.email)
    return TokenResponse(access_token=token)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_endpoint(user_id: int, db: AsyncSession = Depends(get_db)):
    row = await get_user_by_id(db, user_id)
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        full_name=row.full_name,
        email=row.email,
        role=row.role,
        department=row.department or "",
        is_active=row.is_active,
    )


@router.get("", response_model=list[UserResponse])
async def list_users_endpoint(
    tenant_id: str = Query(..., min_length=2, max_length=64),
    role: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    rows = await list_users(db, tenant_id=tenant_id, role=role, limit=limit)
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
