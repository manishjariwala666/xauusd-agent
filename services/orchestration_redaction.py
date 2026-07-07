"""Safe redaction helpers for Master AI orchestration.

The orchestrator must only persist redacted payloads in Master AI tables.  This
module is intentionally dependency-free so it can be reused by planners,
context, message bus, memory, dashboard views, and tests.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

SENSITIVE_KEY_PARTS = (
    "secret",
    "token",
    "password",
    "passwd",
    "authorization",
    "auth_header",
    "api_key",
    "apikey",
    "private_key",
    "service_account",
    "credential",
    "credentials",
    "client_secret",
    "jwt",
    "bearer",
    "cookie",
)

REDACTED = "[REDACTED]"


def is_sensitive_key(key: str) -> bool:
    """Return True when a JSON key is unsafe to display or persist verbatim."""
    normalized = key.lower().replace("-", "_")
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def redact_value(value: Any, *, max_string_length: int = 500) -> Any:
    """Return a redacted, JSON-compatible copy of ``value``.

    This function is deliberately conservative.  It redacts by key name, limits
    large strings, recursively handles nested dictionaries/lists, and avoids
    exposing object representations that may contain credentials.
    """
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            if is_sensitive_key(key):
                redacted[key] = REDACTED
            else:
                redacted[key] = redact_value(
                    raw_value,
                    max_string_length=max_string_length,
                )
        return redacted

    if isinstance(value, (str, bytes)):
        text = value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value
        if len(text) > max_string_length:
            return f"{text[:max_string_length]}…[truncated]"
        return text

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [redact_value(item, max_string_length=max_string_length) for item in value]

    if isinstance(value, (int, float, bool)) or value is None:
        return value

    return str(value)


def safe_error_message(error: BaseException | str | None, *, max_length: int = 500) -> str | None:
    """Return a short, redacted error string suitable for admin UI storage."""
    if error is None:
        return None
    text = str(error)
    text = str(redact_value(text, max_string_length=max_length))
    for marker in ("-----BEGIN", "-----END", "gho_", "xoxb-", "Bearer "):
        if marker in text:
            text = text.replace(marker, REDACTED)
    if len(text) > max_length:
        text = f"{text[:max_length]}…[truncated]"
    return text
