"""
Real LLM test for POST /tickets/ai/agent-run (customer Work with agent).

- Skips if Ollama is not reachable at LOCAL_LLM_BASE_URL (default :11434).
- Uses SQLite so it does not depend on cloud Postgres for the test run.

Run when Ollama is up and model is pulled, e.g.:
  ollama pull llama3.2
  python -m pytest test/test_work_with_agent_live_llm.py -v -s
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import httpx
import pytest

_OLLAMA_TAGS = "http://127.0.0.1:11434/api/tags"


def _ollama_available() -> bool:
    try:
        r = httpx.get(_OLLAMA_TAGS, timeout=2.0)
        return r.status_code == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _ollama_available(),
    reason="Ollama not running (start Ollama and pull LOCAL_LLM_MODEL, e.g. ollama pull llama3.2)",
)


@pytest.fixture(scope="module")
def live_client():
    _db = Path(__file__).resolve().parent / "test_live_llm.sqlite3"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_db.as_posix()}"
    from app.core.config import get_settings

    get_settings.cache_clear()
    from fastapi.testclient import TestClient
    from main import app

    with TestClient(app) as c:
        yield c


def test_work_with_agent_calls_real_llm(live_client):
    """End-to-end: customer + ticket + Work with agent hits Ollama and returns reply + ticket_id."""
    email = f"live_llm_{int(time.time())}@example.com"
    assert live_client.post(
        "/api/v1/users",
        json={
            "full_name": "Live LLM Customer",
            "email": email,
            "password": "Customer@123",
            "role": "customer",
        },
    ).status_code == 200
    tok = live_client.post("/api/v1/users/login", json={"email": email, "password": "Customer@123"}).json().get(
        "access_token"
    )
    assert tok
    h = {"Authorization": f"Bearer {tok}"}
    t = live_client.post(
        "/api/v1/tickets",
        data={
            "title": "Live LLM agent test",
            "description": "Customer asks for a short acknowledgement only. Reply in one or two sentences.",
        },
        headers=h,
    )
    assert t.status_code == 200, t.text
    ticket_id = t.json()["id"]

    r = live_client.post("/api/v1/tickets/ai/agent-run", headers=h)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("ticket_id") == ticket_id
    reply = (data.get("reply") or "").strip()
    assert len(reply) > 10, f"expected non-trivial reply, got: {reply!r}"

    conv = live_client.get(f"/api/v1/tickets/{ticket_id}/conversations", headers=h)
    assert conv.status_code == 200
    assert any(m.get("message_type") == "ai_customer" for m in conv.json())
