"""Webhook helpers and optional FastAPI router for the Master AI Telegram bot.

This module keeps the two Telegram bots fully separated:

* ``/webhooks/telegram`` continues to use ``TELEGRAM_BOT_TOKEN`` and the
  existing signal/reply bot pipeline.
* ``/webhooks/telegram/master`` uses ``MASTER_AI_TELEGRAM_BOT_TOKEN`` and only
  handles private Master AI admin commands.
"""

from __future__ import annotations

from os import getenv
from typing import Any, Callable
import json
import urllib.error
import urllib.request

from services.telegram_master_ai_control import (
    MASTER_AI_BOT,
    MASTER_AI_BOT_TOKEN_ENV,
    MASTER_WEBHOOK_PATH,
    SAFE_TELEGRAM_ERROR,
    SIGNAL_BOT,
    SIGNAL_WEBHOOK_PATH,
    try_handle_telegram_update,
)

Sender = Callable[[int | str, str], None]


def handle_master_telegram_webhook(
    update: dict[str, Any],
    *,
    supabase: Any | None = None,
    sender: Sender | None = None,
    runner: Callable[..., Any] | None = None,
    status_loader: Callable[..., list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Handle POST /webhooks/telegram/master without exposing internals."""
    try:
        kwargs: dict[str, Any] = {
            "sender": sender or send_master_ai_bot_message,
            "supabase": supabase,
            "bot_role": MASTER_AI_BOT,
        }
        if runner is not None:
            kwargs["runner"] = runner
        if status_loader is not None:
            kwargs["status_loader"] = status_loader
        result = try_handle_telegram_update(update, **kwargs)
        return {
            "ok": True,
            "webhook": MASTER_WEBHOOK_PATH,
            "bot": "master_ai",
            "handled": bool(result.handled),
            "status": result.status,
            "run_id": result.run_id,
        }
    except Exception:
        _send_fixed_error_best_effort(update, sender=sender)
        return {
            "ok": False,
            "webhook": MASTER_WEBHOOK_PATH,
            "bot": "master_ai",
            "handled": True,
            "status": "ERROR",
            "message": SAFE_TELEGRAM_ERROR,
        }


def handle_signal_telegram_master_command_guard(update: dict[str, Any]) -> dict[str, Any] | None:
    """Return an early response when /master is sent to the signal bot.

    Call this at the start of the existing ``/webhooks/telegram`` handler.  If it
    returns a dictionary, return that response immediately.  If it returns
    ``None``, continue the existing signal/reply bot flow unchanged.
    """
    result = try_handle_telegram_update(update, bot_role=SIGNAL_BOT)
    if not result.handled:
        return None
    return {
        "ok": True,
        "webhook": SIGNAL_WEBHOOK_PATH,
        "bot": "signal",
        "handled": True,
        "ignored": True,
        "status": result.status,
    }


def send_master_ai_bot_message(chat_id: int | str, text: str) -> None:
    """Send Telegram message with MASTER_AI_TELEGRAM_BOT_TOKEN only.

    Exceptions are intentionally generic.  Callers must translate failures to
    SAFE_TELEGRAM_ERROR for Telegram users.
    """
    token = _master_bot_token()
    if not token:
        raise RuntimeError("Master AI Telegram bot is not configured.")
    payload = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
            if response.status >= 400:
                raise RuntimeError("Telegram send failed.")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError("Telegram send failed.") from exc


def _master_bot_token() -> str:
    token = getenv(MASTER_AI_BOT_TOKEN_ENV) or ""
    if token:
        return token.strip()
    try:
        from config import get_settings

        raw = getattr(get_settings(), "master_ai_telegram_bot_token", "")
        return str(raw or "").strip()
    except Exception:
        return ""


def _send_fixed_error_best_effort(update: dict[str, Any], *, sender: Sender | None) -> None:
    chat_id = _extract_chat_id(update)
    if chat_id is None:
        return
    try:
        (sender or send_master_ai_bot_message)(chat_id, SAFE_TELEGRAM_ERROR)
    except Exception:
        return


def _extract_chat_id(update: dict[str, Any]) -> int | str | None:
    if not isinstance(update, dict):
        return None
    message = (
        update.get("message")
        or update.get("edited_message")
        or update.get("channel_post")
        or update.get("callback_query", {}).get("message")
    )
    if not isinstance(message, dict):
        return None
    chat = message.get("chat") if isinstance(message.get("chat"), dict) else {}
    return chat.get("id")


try:  # Optional FastAPI integration for backend.py.
    from fastapi import APIRouter, Request
except Exception:  # pragma: no cover - FastAPI may be absent in unit-only envs.
    APIRouter = None  # type: ignore[assignment]
    Request = None  # type: ignore[assignment]


if APIRouter is not None:
    router = APIRouter()

    @router.post(MASTER_WEBHOOK_PATH)
    async def telegram_master_webhook(request: Request) -> dict[str, Any]:  # type: ignore[valid-type]
        try:
            update = await request.json()
        except Exception:
            update = {}
        return handle_master_telegram_webhook(update)
else:  # pragma: no cover
    router = None
