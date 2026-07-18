"""Webhook helpers and optional FastAPI router for the Master AI Telegram bot.

This module keeps the two Telegram bots fully separated:

* ``/webhooks/telegram`` continues to use ``TELEGRAM_BOT_TOKEN`` and the
  existing signal/reply bot pipeline.
* ``/webhooks/telegram/master`` uses ``MASTER_AI_TELEGRAM_BOT_TOKEN`` and only
  handles private Master AI admin commands.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from os import getenv
from threading import RLock
from typing import Any, Callable
from time import time
import json
import urllib.error
import urllib.request

from services.telegram_master_ai_control import (
    MASTER_AI_BOT,
    MASTER_AI_BOT_TOKEN_ENV,
    MASTER_WEBHOOK_PATH,
    MasterTelegramCommandResult,
    SAFE_TELEGRAM_ERROR,
    SIGNAL_BOT,
    SIGNAL_WEBHOOK_PATH,
    try_handle_telegram_update,
)

Sender = Callable[[int | str, str], None]

_DEDUPE_TTL_SECONDS = 300
_UPDATE_LOCK_STRIPES = tuple(RLock() for _ in range(64))
_UPDATE_STATE_LOCK = RLock()


@dataclass(frozen=True)
class _MasterUpdateIdentity:
    bot_role: str
    webhook_source: str
    chat_id: str
    sender_user_id: str
    command_identity: str


@dataclass(frozen=True)
class _PendingMasterDelivery:
    created_at: float
    identity: _MasterUpdateIdentity
    result: MasterTelegramCommandResult


_SEEN_MASTER_UPDATE_KEYS: dict[
    str,
    tuple[float, _MasterUpdateIdentity],
] = {}
_PENDING_MASTER_DELIVERIES: dict[str, _PendingMasterDelivery] = {}


class MasterTelegramDeliveryError(RuntimeError):
    """Raised when Telegram did not confirm delivery of a Master AI reply."""


def _master_update_identity(
    update: dict[str, Any],
    *,
    bot_role: str,
    webhook_source: str,
) -> _MasterUpdateIdentity:
    message = _extract_message_payload(update)
    chat = message.get("chat") if isinstance(message.get("chat"), dict) else {}
    callback = update.get("callback_query") if isinstance(update, dict) else {}
    callback_sender = (
        callback.get("from")
        if isinstance(callback, dict) and isinstance(callback.get("from"), dict)
        else {}
    )
    message_sender = (
        message.get("from") if isinstance(message.get("from"), dict) else {}
    )
    sender = callback_sender or message_sender
    text = str(message.get("text") or message.get("caption") or "").strip()
    return _MasterUpdateIdentity(
        bot_role=str(bot_role or MASTER_AI_BOT),
        webhook_source=str(webhook_source or MASTER_WEBHOOK_PATH),
        chat_id=str(chat.get("id") or ""),
        sender_user_id=str(sender.get("id") or ""),
        command_identity=hashlib.sha256(text.encode("utf-8")).hexdigest(),
    )


def _master_update_key(
    update: dict[str, Any],
    *,
    bot_role: str = MASTER_AI_BOT,
    webhook_source: str = MASTER_WEBHOOK_PATH,
) -> str:
    """Build stable key for Telegram duplicate update protection."""
    safe_update = update if isinstance(update, dict) else {}
    identity = _master_update_identity(
        safe_update,
        bot_role=bot_role,
        webhook_source=webhook_source,
    )
    message = _extract_message_payload(safe_update)
    chat = message.get("chat") if isinstance(message.get("chat"), dict) else {}
    update_id = safe_update.get("update_id")
    message_id = message.get("message_id")
    namespace = f"{identity.bot_role}:{identity.webhook_source}"
    identity_suffix = (
        f"chat:{identity.chat_id}:sender:{identity.sender_user_id}:"
        f"command:{identity.command_identity}"
    )
    if update_id is not None:
        return f"{namespace}:update:{update_id}:{identity_suffix}"
    if chat.get("id") and message_id is not None:
        return f"{namespace}:message:{message_id}:{identity_suffix}"
    return f"{namespace}:fallback:{identity_suffix}"


def _extract_message_payload(update: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(update, dict):
        return {}
    message = (
        update.get("message")
        or update.get("edited_message")
        or update.get("channel_post")
        or update.get("callback_query", {}).get("message")
        or {}
    )
    return message if isinstance(message, dict) else {}


def _update_lock(update_key: str) -> RLock:
    digest = hashlib.sha256(update_key.encode("utf-8")).digest()
    return _UPDATE_LOCK_STRIPES[int.from_bytes(digest[:2], "big") % len(_UPDATE_LOCK_STRIPES)]


def _is_duplicate_master_update(
    update_key: str,
    identity: _MasterUpdateIdentity,
) -> bool:
    """Return True only after the update reply was delivered successfully."""
    now = time()
    with _UPDATE_STATE_LOCK:
        expired = [
            key
            for key, (seen_at, _) in _SEEN_MASTER_UPDATE_KEYS.items()
            if now - seen_at > _DEDUPE_TTL_SECONDS
        ]
        for key in expired:
            _SEEN_MASTER_UPDATE_KEYS.pop(key, None)
        expired_pending = [
            key
            for key, pending in _PENDING_MASTER_DELIVERIES.items()
            if now - pending.created_at > _DEDUPE_TTL_SECONDS
        ]
        for key in expired_pending:
            _PENDING_MASTER_DELIVERIES.pop(key, None)
        seen = _SEEN_MASTER_UPDATE_KEYS.get(update_key)
        return seen is not None and seen[1] == identity


def _pending_result(
    update_key: str,
    identity: _MasterUpdateIdentity,
) -> MasterTelegramCommandResult | None:
    with _UPDATE_STATE_LOCK:
        pending = _PENDING_MASTER_DELIVERIES.get(update_key)
    if pending is None or pending.identity != identity:
        return None
    result_chat_id = str(pending.result.chat_id or "")
    if result_chat_id != identity.chat_id:
        return None
    return pending.result



def handle_master_telegram_webhook(
    update: dict[str, Any],
    *,
    supabase: Any | None = None,
    sender: Sender | None = None,
    runner: Callable[..., Any] | None = None,
    status_loader: Callable[..., list[dict[str, Any]]] | None = None,
    bot_role: str = MASTER_AI_BOT,
    webhook_source: str = MASTER_WEBHOOK_PATH,
) -> dict[str, Any]:
    """Handle POST /webhooks/telegram/master without exposing internals."""
    identity = _master_update_identity(
        update,
        bot_role=bot_role,
        webhook_source=webhook_source,
    )
    update_key = _master_update_key(
        update,
        bot_role=bot_role,
        webhook_source=webhook_source,
    )
    with _update_lock(update_key):
        try:
            if _is_duplicate_master_update(update_key, identity):
                return {
                    "ok": True,
                    "webhook": webhook_source,
                    "bot": "master_ai",
                    "handled": False,
                    "duplicate": True,
                    "status": "DUPLICATE_IGNORED",
                    "run_id": None,
                }

            result = _pending_result(update_key, identity)
            if result is None:
                kwargs: dict[str, Any] = {
                    "supabase": supabase,
                    "bot_role": bot_role,
                }
                if runner is not None:
                    kwargs["runner"] = runner
                if status_loader is not None:
                    kwargs["status_loader"] = status_loader
                result = try_handle_telegram_update(update, **kwargs)
                if str(result.chat_id or "") != identity.chat_id:
                    raise RuntimeError("Master Telegram response identity mismatch.")
                with _UPDATE_STATE_LOCK:
                    _PENDING_MASTER_DELIVERIES[update_key] = _PendingMasterDelivery(
                        created_at=time(),
                        identity=identity,
                        result=result,
                    )

            if result.response_text is not None and result.chat_id is not None:
                try:
                    (sender or send_master_ai_bot_message)(
                        result.chat_id,
                        result.response_text,
                    )
                except Exception as exc:
                    raise MasterTelegramDeliveryError(
                        "Master AI Telegram reply delivery failed."
                    ) from exc

            with _UPDATE_STATE_LOCK:
                _PENDING_MASTER_DELIVERIES.pop(update_key, None)
                _SEEN_MASTER_UPDATE_KEYS[update_key] = (time(), identity)
            return {
                "ok": True,
                "webhook": webhook_source,
                "bot": "master_ai",
                "handled": bool(result.handled),
                "status": result.status,
                "run_id": result.run_id,
            }
        except MasterTelegramDeliveryError:
            raise
        except Exception:
            try:
                _send_fixed_error(update, sender=sender)
            except Exception as exc:
                raise MasterTelegramDeliveryError(
                    "Master AI Telegram error reply delivery failed."
                ) from exc
            with _UPDATE_STATE_LOCK:
                _PENDING_MASTER_DELIVERIES.pop(update_key, None)
                _SEEN_MASTER_UPDATE_KEYS[update_key] = (time(), identity)
            return {
                "ok": False,
                "webhook": webhook_source,
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
            try:
                body = json.loads(response.read().decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise RuntimeError("Telegram send failed.") from exc
            if not isinstance(body, dict) or body.get("ok") is not True:
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


def _send_fixed_error(update: dict[str, Any], *, sender: Sender | None) -> None:
    chat_id = _extract_chat_id(update)
    if chat_id is None:
        return
    (sender or send_master_ai_bot_message)(chat_id, SAFE_TELEGRAM_ERROR)


def _send_fixed_error_best_effort(
    update: dict[str, Any],
    *,
    sender: Sender | None,
) -> None:
    """Preserve the existing non-raising helper for external callers."""
    try:
        _send_fixed_error(update, sender=sender)
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
