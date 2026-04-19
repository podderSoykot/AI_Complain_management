"""Tests for Work with agent (mocked LLM). Forces SQLite after .env so TestClient is stable."""

from __future__ import annotations

import os
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings

# app.core.config already ran load_dotenv; override for this test module before engine import.
_TEST_DB = Path(__file__).resolve().parent / "test_ai_agent.sqlite3"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB.as_posix()}"
get_settings.cache_clear()

from main import app  # noqa: E402


@pytest.fixture(scope="module")
def client() -> TestClient:
    """One client for the whole module so the async loop/engine stay valid across tests."""
    with TestClient(app) as c:
        yield c


def _mock_settings():
    from types import SimpleNamespace

    return SimpleNamespace(
        llm_mode="api",
        openai_api_key="test-key",
        openai_api_base="https://api.openai.com/v1",
        ai_model="gpt-4o-mini",
        local_llm_base_url="http://127.0.0.1:11434/v1",
        local_llm_model="llama3.2",
        local_llm_api_key="",
    )


def test_customer_agent_run_requires_auth(client: TestClient):
    r = client.post("/api/v1/tickets/ai/agent-run")
    assert r.status_code == 401


def test_customer_agent_no_active_ticket(client: TestClient):
    email = f"ai_empty_{int(time.time())}@example.com"
    assert client.post(
        "/api/v1/users",
        json={
            "full_name": "No Ticket User",
            "email": email,
            "password": "Customer@123",
            "role": "customer",
        },
    ).status_code == 200
    tok = client.post("/api/v1/users/login", json={"email": email, "password": "Customer@123"}).json().get(
        "access_token"
    )
    r = client.post("/api/v1/tickets/ai/agent-run", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 400
    detail = (r.json().get("detail") or "").lower()
    assert "ticket" in detail or "active" in detail


def test_customer_agent_success_with_mock(client: TestClient):
    email = f"ai_ok_{int(time.time())}@example.com"
    assert client.post(
        "/api/v1/users",
        json={
            "full_name": "Agent Test Customer",
            "email": email,
            "password": "Customer@123",
            "role": "customer",
        },
    ).status_code == 200
    tok = client.post("/api/v1/users/login", json={"email": email, "password": "Customer@123"}).json().get(
        "access_token"
    )
    headers = {"Authorization": f"Bearer {tok}"}
    t = client.post(
        "/api/v1/tickets",
        data={
            "title": "Agent test ticket",
            "description": "This ticket is for automated agent testing with a mocked LLM.",
        },
        headers=headers,
    )
    assert t.status_code == 200
    ticket_id = t.json()["id"]

    mock_reply = "Mock agent: I have reviewed your ticket and suggest waiting for staff confirmation."

    with patch("app.features.tickets.ai_support._ensure_ai_config", new_callable=AsyncMock, return_value=_mock_settings()):
        with patch("app.features.tickets.ai_support.chat_completion", new_callable=AsyncMock, return_value=mock_reply):
            r = client.post("/api/v1/tickets/ai/agent-run", headers=headers)

    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("ticket_id") == ticket_id
    assert mock_reply in (data.get("reply") or "")

    conv = client.get(f"/api/v1/tickets/{ticket_id}/conversations", headers=headers)
    assert conv.status_code == 200
    msgs = conv.json()
    assert any(m.get("message_type") == "ai_customer" for m in msgs)


def test_admin_agent_success_with_mock(client: TestClient):
    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    login = client.post("/api/v1/users/login/admin", json={"email": admin_email, "password": admin_password})
    if login.status_code != 200:
        pytest.skip("Admin login not available in this environment")
    admin_tok = login.json().get("access_token")
    admin_headers = {"Authorization": f"Bearer {admin_tok}"}

    cust_email = f"ai_admin_ctx_{int(time.time())}@example.com"
    assert client.post(
        "/api/v1/users",
        json={
            "full_name": "Ctx Customer",
            "email": cust_email,
            "password": "Customer@123",
            "role": "customer",
        },
    ).status_code == 200
    ctok = client.post("/api/v1/users/login", json={"email": cust_email, "password": "Customer@123"}).json().get(
        "access_token"
    )
    ch = {"Authorization": f"Bearer {ctok}"}
    t = client.post(
        "/api/v1/tickets",
        data={
            "title": "Ticket for admin agent test",
            "description": "Enough text for validation rules on ticket create for admin agent path.",
        },
        headers=ch,
    )
    assert t.status_code == 200
    ticket_id = t.json()["id"]

    json_body = '{"assistant_reply":"Mock admin triage complete.","mark_resolved":false,"resolution_summary":""}'

    with patch("app.features.tickets.ai_support._ensure_ai_config", new_callable=AsyncMock, return_value=_mock_settings()):
        with patch("app.features.tickets.ai_support.chat_completion", new_callable=AsyncMock, return_value=json_body):
            r = client.post("/api/v1/admin/tickets/ai/agent-run", headers=admin_headers)

    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("ticket_id") == ticket_id
    assert "Mock admin triage" in (data.get("reply") or "")
    assert data.get("resolution_applied") is False
