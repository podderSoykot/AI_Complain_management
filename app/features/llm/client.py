"""
OpenAI-compatible Chat Completions over HTTP (httpx).

Supports:
- LLM_MODE=local  → default Ollama at http://127.0.0.1:11434/v1 (no API key required)
- LLM_MODE=api    → OpenAI / Azure / other proxy using OPENAI_API_KEY + OPENAI_API_BASE
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import Settings, get_settings


async def chat_completion(
    *,
    messages: list[dict[str, str]],
    temperature: float = 0.35,
    json_mode: bool = False,
    timeout_s: float | None = None,
    settings: Settings | None = None,
) -> str:
    """
    POST {base}/chat/completions (OpenAI-compatible).
    Returns assistant message content (string).

    When ``timeout_s`` is None, uses ``local_llm_timeout_seconds`` (local) or
    ``openai_timeout_seconds`` (api) from settings.
    """
    s = settings or get_settings()
    mode = (s.llm_mode or "local").strip().lower()
    if mode not in ("local", "api"):
        mode = "api"

    if mode == "local":
        base_url = (s.local_llm_base_url or "").rstrip("/")
        api_key = (s.local_llm_api_key or "").strip()
        model = (s.local_llm_model or s.ai_model or "").strip()
    else:
        base_url = (s.openai_api_base or "").rstrip("/")
        api_key = (s.openai_api_key or "").strip()
        model = (s.ai_model or "").strip()
        if not api_key:
            raise RuntimeError("Missing OPENAI_API_KEY (LLM_MODE=api).")

    if not base_url:
        raise RuntimeError("LLM base URL is not configured.")
    if not model:
        raise RuntimeError("LLM model name is not configured.")

    if timeout_s is None:
        timeout_s = (
            float(s.local_llm_timeout_seconds) if mode == "local" else float(s.openai_timeout_seconds)
        )

    url = f"{base_url}/chat/completions"
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    async with httpx.AsyncClient(timeout=timeout_s) as client:
        res = await client.post(url, headers=headers, json=payload)
        res.raise_for_status()
        data = res.json()

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("AI response missing choices")
    msg = (choices[0].get("message") or {}).get("content")
    if not isinstance(msg, str) or not msg.strip():
        raise RuntimeError("AI response missing content")
    return msg.strip()
