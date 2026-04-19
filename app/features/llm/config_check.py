"""Validate LLM settings for the active mode (local OpenAI-compatible vs remote API key)."""

from __future__ import annotations

from app.core.config import Settings


def assert_llm_configured(settings: Settings) -> None:
    mode = (settings.llm_mode or "local").strip().lower()
    if mode not in ("local", "api"):
        mode = "api"

    if mode == "local":
        base = (settings.local_llm_base_url or "").strip()
        if not base:
            raise RuntimeError(
                "LLM_MODE=local but LOCAL_LLM_BASE_URL is empty. "
                "Example: http://127.0.0.1:11434/v1 (Ollama OpenAI-compatible API)."
            )
        model = (settings.local_llm_model or settings.ai_model or "").strip()
        if not model:
            raise RuntimeError("Set LOCAL_LLM_MODEL (e.g. llama3.2) or AI_MODEL for local LLM.")
        return

    if not (settings.openai_api_key or "").strip():
        raise RuntimeError(
            "LLM_MODE=api requires OPENAI_API_KEY, or switch to LLM_MODE=local for Ollama/LM Studio."
        )
