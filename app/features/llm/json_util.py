"""JSON helpers for LLM outputs."""

from __future__ import annotations

import json
from typing import Any


def safe_parse_json_object(text: str) -> dict[str, Any] | None:
    try:
        out = json.loads(text)
        return out if isinstance(out, dict) else None
    except json.JSONDecodeError:
        return None
