"""Human-readable details for httpx errors from LLM providers."""

from __future__ import annotations

import httpx


def format_llm_http_error(exc: httpx.HTTPError) -> str:
    parts: list[str] = [type(exc).__name__]
    s = str(exc).strip()
    if s:
        parts.append(s)
    if isinstance(exc, httpx.HTTPStatusError):
        try:
            body = exc.response.text.strip()
            if body:
                parts.append(body[:500])
        except Exception:
            pass
        try:
            parts.append(f"url={exc.request.url!s}")
        except Exception:
            pass
    if len(parts) == 1:
        parts.append(repr(exc))
    return "; ".join(parts)
