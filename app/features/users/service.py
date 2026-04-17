from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import hash_password, verify_password
from app.core.config import get_settings
from app.features.users.models import User
from app.features.users.schemas import UserCreate

settings = get_settings()


def _auto_tenant_id_from_email(email: str) -> str:
    # Deterministic tenant key by email domain (e.g., user@acme.com -> acme_com).
    domain = email.split("@", 1)[1].lower() if "@" in email else "public"
    tenant = domain.replace(".", "_").replace("-", "_")
    return tenant[:64] or "public"


async def create_user(db: AsyncSession, payload: UserCreate) -> User:
    normalized_email = str(payload.email).lower()
    user = User(
        tenant_id=_auto_tenant_id_from_email(normalized_email),
        full_name=payload.full_name,
        email=normalized_email,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_by_id(db: AsyncSession, user_id: int):
    stmt = (
        select(
            User.id,
            User.tenant_id,
            User.full_name,
            User.email,
            User.role,
            User.is_active,
        )
        .where(User.id == user_id)
        .limit(1)
    )
    return (await db.execute(stmt)).first()


async def get_user_by_email(db: AsyncSession, email: str):
    stmt = (
        select(
            User.id,
            User.tenant_id,
            User.full_name,
            User.email,
            User.password_hash,
            User.role,
            User.is_active,
        )
        .where(User.email == email.lower())
        .limit(1)
    )
    return (await db.execute(stmt)).first()


async def list_users(db: AsyncSession, tenant_id: str, role: str | None, limit: int = 50):
    where_clause = User.tenant_id == tenant_id
    if role:
        where_clause = and_(where_clause, User.role == role)

    stmt = (
        select(
            User.id,
            User.tenant_id,
            User.full_name,
            User.email,
            User.role,
            User.is_active,
        )
        .where(where_clause)
        .order_by(User.id.desc())
        .limit(limit)
    )
    return (await db.execute(stmt)).all()


async def authenticate_user(db: AsyncSession, email: str, password: str):
    row = await get_user_by_email(db, email)
    if not row or not row.password_hash:
        return None
    if not verify_password(password, row.password_hash):
        return None
    return row


async def ensure_admin_user(db: AsyncSession) -> None:
    admin_email = settings.admin_email.lower()
    existing = await get_user_by_email(db, admin_email)
    if existing:
        return

    admin_user = User(
        tenant_id=settings.admin_tenant_id,
        full_name="System Admin",
        email=admin_email,
        password_hash=hash_password(settings.admin_password),
        role="admin",
        is_active=1,
    )
    db.add(admin_user)
    await db.commit()


async def list_all_users(db: AsyncSession, limit: int = 100):
    stmt = (
        select(
            User.id,
            User.tenant_id,
            User.full_name,
            User.email,
            User.role,
            User.is_active,
        )
        .order_by(User.id.desc())
        .limit(limit)
    )
    return (await db.execute(stmt)).all()
