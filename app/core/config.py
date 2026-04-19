from functools import lru_cache
import os
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")


def _get_env(*keys: str, default: str) -> str:
    for key in keys:
        value = os.getenv(key)
        if value:
            return value
    return default


def _normalize_database_url(url: str) -> str:
    # Support common .env formats and force async SQLAlchemy driver for Postgres.
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # asyncpg does not accept sslmode; use ssl=require for URL param style.
    if "sslmode=require" in url:
        url = url.replace("sslmode=require", "ssl=require")
    return url


class Settings(BaseModel):
    app_name: str = "AI Complaint Management API"
    database_url: str = _normalize_database_url(
        _get_env("DATABASE_URL", "Database_url", "database_url", default="sqlite+aiosqlite:///./complaints.db")
    )
    ticket_upload_dir: str = _get_env("TICKET_UPLOAD_DIR", "ticket_upload_dir", default=str(ROOT_DIR / "uploads" / "tickets"))
    ticket_max_upload_bytes: int = int(_get_env("TICKET_MAX_UPLOAD_BYTES", "ticket_max_upload_bytes", default=str(10 * 1024 * 1024)))
    ticket_max_files_per_ticket: int = int(_get_env("TICKET_MAX_FILES", "ticket_max_files", default="8"))
    jwt_secret_key: str = _get_env("JWT_SECRET_KEY", "jwt_secret_key", default="change_this_secret")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    admin_email: str = _get_env("ADMIN_EMAIL", "admin_email", default="admin@example.com")
    admin_password: str = _get_env("ADMIN_PASSWORD", "admin_password", default="admin123")
    admin_tenant_id: str = _get_env("ADMIN_TENANT_ID", "admin_tenant_id", default="system")
    max_workers_thread: int = 8
    max_workers_process: int = 2
    # LLM_MODE: "local" (Ollama / LM Studio OpenAI-compatible) or "api" (OpenAI key).
    llm_mode: str = _get_env("LLM_MODE", "llm_mode", default="local").strip().lower()
    local_llm_base_url: str = _get_env(
        "LOCAL_LLM_BASE_URL",
        "local_llm_base_url",
        default="http://127.0.0.1:11434/v1",
    )
    local_llm_model: str = _get_env("LOCAL_LLM_MODEL", "local_llm_model", default="llama3.2:3b")
    local_llm_api_key: str = _get_env("LOCAL_LLM_API_KEY", "local_llm_api_key", default="")
    local_llm_timeout_seconds: float = float(
        _get_env("LOCAL_LLM_TIMEOUT_SECONDS", "local_llm_timeout_seconds", default="600")
    )
    # Remote OpenAI-compatible Chat Completions (when LLM_MODE=api).
    openai_api_key: str = _get_env("OPENAI_API_KEY", "openai_api_key", default="")
    openai_api_base: str = _get_env("OPENAI_API_BASE", "openai_api_base", default="https://api.openai.com/v1")
    openai_timeout_seconds: float = float(
        _get_env("OPENAI_TIMEOUT_SECONDS", "openai_timeout_seconds", default="120")
    )
    ai_model: str = _get_env("AI_MODEL", "ai_model", default="gpt-4o-mini")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
