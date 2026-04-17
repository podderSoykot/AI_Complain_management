from sqlalchemy import func, select
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.features.tickets.router import router as tickets_router
from app.features.users.router import router as users_router
from app.features.admin.router import router as admin_router
from app.database.session import SessionLocal, engine
from app.core.perf import add_process_time_header
from app.database.base import Base
from app.core.config import get_settings
from app.features.agents.models import Agent
from app.features.tickets import models as _ticket_models  # noqa: F401
from app.features.users import models as _user_models  # noqa: F401
from app.features.users.service import ensure_admin_user


app = FastAPI(title="AI Complaint Management API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(add_process_time_header)
app.include_router(tickets_router)
app.include_router(users_router)
app.include_router(admin_router)


@app.on_event("startup")
async def startup():
    settings = get_settings()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Lightweight compatibility migration for existing users table.
        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255) DEFAULT ''"))
        except Exception:
            # Safe fallback for databases that don't support IF NOT EXISTS.
            try:
                await conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255) DEFAULT ''"))
            except Exception:
                pass

    # Seed agents once (explicit count query, no SELECT *).
    async with SessionLocal() as session:
        count_stmt = select(func.count()).select_from(Agent)
        count = (await session.execute(count_stmt)).scalar_one()
        if count == 0:
            session.add_all(
                [
                    Agent(name="Sara", skills="billing,complaint", current_load=0),
                    Agent(name="Imran", skills="account,technical", current_load=0),
                    Agent(name="Nabila", skills="technical,billing", current_load=0),
                ]
            )
            await session.commit()
        # Ensure admin account from .env exists.
        if settings.admin_email and settings.admin_password:
            await ensure_admin_user(session)
