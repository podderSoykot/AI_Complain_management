"""LLM integration: local (Ollama-compatible) or remote API key."""

from app.features.llm.client import chat_completion
from app.features.llm.config_check import assert_llm_configured
from app.features.llm.json_util import safe_parse_json_object

__all__ = ["assert_llm_configured", "chat_completion", "safe_parse_json_object"]
