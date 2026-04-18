from sqlalchemy import and_, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import hash_password, verify_password
from app.core.config import get_settings
from app.features.tickets.models import Ticket
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
        department=payload.department or "",
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
            User.department,
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
            User.department,
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
            User.department,
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
        # Keep admin credentials in sync with .env to avoid stale password issues.
        user_obj = await db.get(User, existing.id)
        if user_obj is None:
            return

        changed = False
        if user_obj.role != "admin":
            user_obj.role = "admin"
            changed = True
        if user_obj.tenant_id != settings.admin_tenant_id:
            user_obj.tenant_id = settings.admin_tenant_id
            changed = True
        if not verify_password(settings.admin_password, user_obj.password_hash):
            user_obj.password_hash = hash_password(settings.admin_password)
            changed = True
        if user_obj.is_active != 1:
            user_obj.is_active = 1
            changed = True

        if changed:
            await db.commit()
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
            User.department,
            User.is_active,
        )
        .order_by(User.id.desc())
        .limit(limit)
    )
    return (await db.execute(stmt)).all()


async def update_user_status(db: AsyncSession, user_id: int, is_active: int):
    user_obj = await db.get(User, user_id)
    if user_obj is None:
        return None
    user_obj.is_active = is_active
    await db.commit()
    await db.refresh(user_obj)
    return user_obj


async def update_user_role(db: AsyncSession, user_id: int, role: str):
    user_obj = await db.get(User, user_id)
    if user_obj is None:
        return None
    user_obj.role = role
    if role not in ("support_agent", "supervisor"):
        user_obj.department = ""
    await db.commit()
    await db.refresh(user_obj)
    return user_obj


async def update_user_by_admin(
    db: AsyncSession,
    user_id: int,
    *,
    full_name: str | None = None,
    email: str | None = None,
    role: str | None = None,
    department: str | None = None,
    is_active: int | None = None,
) -> tuple[User | None, str | None]:
    user_obj = await db.get(User, user_id)
    if user_obj is None:
        return None, "not_found"

    if email is not None:
        normalized_email = str(email).lower()
        existing = await get_user_by_email(db, normalized_email)
        if existing and existing.id != user_id:
            return None, "email_taken"
        user_obj.email = normalized_email
        user_obj.tenant_id = _auto_tenant_id_from_email(normalized_email)

    if full_name is not None:
        user_obj.full_name = full_name
    if role is not None:
        user_obj.role = role
    if department is not None:
        user_obj.department = (department or "").strip()[:80]
    if user_obj.role not in ("support_agent", "supervisor"):
        user_obj.department = ""
    if is_active is not None:
        user_obj.is_active = is_active

    await db.commit()
    await db.refresh(user_obj)
    return user_obj, None


async def delete_user_by_admin(db: AsyncSession, user_id: int, admin_user_id: int) -> str | None:
    if user_id == admin_user_id:
        return "cannot_delete_self"
    user_obj = await db.get(User, user_id)
    if user_obj is None:
        return "not_found"
    await db.execute(update(Ticket).where(Ticket.assignee_id == user_id).values(assignee_id=None))
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()
    return None
