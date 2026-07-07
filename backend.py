"""FastAPI webhook backend for production Telegram and WhatsApp events."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query, Request, Response
from loguru import logger
import requests
from sqlalchemy import text

from config import get_settings
from core.database import session_scope
from services.conversation_service import record_inbound_message
from services.migration_service import apply_pending_migrations
from services.telegram_master_ai_control import try_handle_telegram_update
from services.telegram_master_ai_webhook import (
    handle_master_telegram_webhook,
    handle_signal_telegram_master_command_guard,
)
from services.telegram_service import TelegramService


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Apply migrations once, then serve until Render shuts down."""
    apply_pending_migrations()
    _configure_telegram_webhook()
    yield


app = FastAPI(
    title="AI Market Analytics Pro Backend",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)



@app.get("/health")
def health() -> dict[str, str]:
    """Return service and database health without exposing configuration."""
    with session_scope() as session:
        session.execute(text("SELECT 1"))
    return {"status": "healthy"}


@app.get("/sitemap.xml")
def sitemap() -> Response:
    """Serve the latest SEO-agent generated sitemap."""
    return Response(_public_setting("SEO_SITEMAP_XML"), media_type="application/xml")


@app.get("/robots.txt")
def robots() -> Response:
    """Serve the latest SEO-agent generated crawler rules."""
    return Response(_public_setting("SEO_ROBOTS_TXT"), media_type="text/plain")



@app.post("/webhooks/telegram/master")
async def telegram_master_ai_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, Any]:
    """Receive Master AI Telegram bot updates."""
    expected = get_settings().telegram_webhook_secret
    if not expected:
        raise HTTPException(503, "Telegram webhook is not configured.")
    if not hmac.compare_digest(x_telegram_bot_api_secret_token or "", expected):
        raise HTTPException(403, "Invalid webhook signature.")

    payload = await request.json()
    return handle_master_telegram_webhook(payload)


@app.post("/webhooks/telegram")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, bool]:
    """Validate Telegram webhook secret and queue inbound messages."""
    expected = get_settings().telegram_webhook_secret
    if not expected:
        raise HTTPException(503, "Telegram webhook is not configured.")
    if not hmac.compare_digest(
        x_telegram_bot_api_secret_token or "", expected
    ):
        raise HTTPException(403, "Invalid webhook signature.")
    payload = await request.json()

    ignored_master_command = handle_signal_telegram_master_command_guard(payload)
    if ignored_master_command is not None:
        return {"accepted": True}

    master_result = try_handle_telegram_update(
        payload,
        sender=lambda chat_id, text: TelegramService().send_text(
            str(chat_id),
            text,
        ),
    )
    if master_result.handled:
        return {"accepted": True}

    message = payload.get("message") or payload.get("edited_message")
    if not message or message.get("from", {}).get("is_bot"):
        return {"accepted": True}
    text_body = message.get("text") or message.get("caption") or ""
    media = _telegram_media(message)
    record_inbound_message(
        channel="TELEGRAM",
        external_user_id=str(message["chat"]["id"]),
        external_message_id=str(message["message_id"]),
        body=text_body or f"[{media.get('type', 'media')}]",
        media=media,
    )
    return {"accepted": True}


@app.get("/webhooks/whatsapp")
def verify_whatsapp(
    mode: str = Query(alias="hub.mode"),
    verify_token: str = Query(alias="hub.verify_token"),
    challenge: str = Query(alias="hub.challenge"),
) -> str:
    """Complete Meta webhook verification."""
    settings = get_settings()
    if mode != "subscribe" or not hmac.compare_digest(
        verify_token, settings.whatsapp_verify_token
    ):
        raise HTTPException(403, "Webhook verification failed.")
    return challenge


@app.post("/webhooks/whatsapp")
async def whatsapp_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
) -> dict[str, str]:
    """Validate Meta signature and queue inbound WhatsApp messages."""
    raw = await request.body()
    settings = get_settings()
    if not settings.meta_app_secret:
        raise HTTPException(503, "Meta webhook is not configured.")
    expected = "sha256=" + hmac.new(
        settings.meta_app_secret.encode(),
        raw,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(x_hub_signature_256 or "", expected):
        raise HTTPException(403, "Invalid webhook signature.")
    payload: dict[str, Any] = json.loads(raw)
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            for message in change.get("value", {}).get("messages", []):
                body, media = _whatsapp_content(message)
                record_inbound_message(
                    channel="WHATSAPP",
                    external_user_id=str(message["from"]),
                    external_message_id=str(message["id"]),
                    body=body,
                    media=media,
                )
    return {"status": "accepted"}


def _telegram_media(message: dict[str, Any]) -> dict[str, Any]:
    for media_type in ("photo", "document", "video", "audio", "voice"):
        if message.get(media_type):
            value = message[media_type]
            item = value[-1] if isinstance(value, list) else value
            return {"type": media_type, "file_id": item.get("file_id")}
    return {}


def _whatsapp_content(message: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    kind = str(message.get("type") or "unknown")
    if kind == "text":
        return str(message.get("text", {}).get("body") or ""), {}
    media = dict(message.get(kind) or {})
    return (
        str(media.get("caption") or f"[{kind}]"),
        {"type": kind, "id": media.get("id"), "mime_type": media.get("mime_type")},
    )


def _public_setting(key: str) -> str:
    with session_scope() as session:
        value = session.execute(
            text(
                """
                SELECT setting_value FROM public.site_settings
                WHERE setting_key = :key AND is_sensitive = FALSE
                """
            ),
            {"key": key},
        ).scalar_one_or_none()
    if value is None:
        raise HTTPException(404, "SEO resource has not been generated.")
    return str(value)


def _configure_telegram_webhook() -> None:
    """Register Telegram webhooks for Signal Bot and Master AI Bot without logging secrets."""
    settings = get_settings()

    public_api_url = str(
        getattr(settings, "public_api_url", "")
        or getattr(settings, "backend_base_url", "")
        or os.getenv("PUBLIC_API_URL", "")
    ).strip()

    webhook_secret = str(
        getattr(settings, "telegram_webhook_secret", "")
        or os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
    ).strip()

    signal_token = str(
        getattr(settings, "telegram_bot_token", "")
        or os.getenv("TELEGRAM_BOT_TOKEN", "")
    ).strip()

    master_token = str(
        getattr(settings, "master_ai_telegram_bot_token", "")
        or os.getenv("MASTER_AI_TELEGRAM_BOT_TOKEN", "")
    ).strip()

    if not public_api_url or not webhook_secret:
        logger.warning("Telegram webhook registration skipped: configuration missing")
        return

    _register_single_telegram_webhook(
        bot_name="signal",
        token=signal_token,
        public_api_url=public_api_url,
        path="/webhooks/telegram",
        webhook_secret=webhook_secret,
    )

    _register_single_telegram_webhook(
        bot_name="master_ai",
        token=master_token,
        public_api_url=public_api_url,
        path="/webhooks/telegram/master",
        webhook_secret=webhook_secret,
    )


def _register_single_telegram_webhook(
    *,
    bot_name: str,
    token: str,
    public_api_url: str,
    path: str,
    webhook_secret: str,
) -> None:
    """Register one Telegram bot webhook without exposing token values."""
    if not token:
        logger.warning("Telegram %s webhook registration skipped: token missing", bot_name)
        return

    webhook_url = public_api_url.rstrip("/") + path
    telegram_url = f"https://api.telegram.org/bot{token}/setWebhook"

    try:
        response = requests.post(
            telegram_url,
            json={
                "url": webhook_url,
                "secret_token": webhook_secret,
                "allowed_updates": ["message", "edited_message"],
                "drop_pending_updates": False,
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            raise RuntimeError("Telegram rejected webhook registration.")
    except Exception:
        logger.exception("Telegram %s webhook registration failed", bot_name)
    else:
        logger.info("Telegram %s webhook registered successfully at %s", bot_name, path)


