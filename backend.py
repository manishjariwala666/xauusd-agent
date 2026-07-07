"""FastAPI webhook backend for production Telegram and WhatsApp events."""

from __future__ import annotations

import hashlib
import hmac
import json
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
    """Register the production webhook without logging credentials."""
    settings = get_settings()
    if not all(
        (
            settings.backend_base_url,
            settings.telegram_bot_token,
            settings.telegram_webhook_secret,
        )
    ):
        logger.warning(
            "Telegram webhook registration skipped: configuration missing"
        )
        return
    endpoint = (
        f"https://api.telegram.org/bot{settings.telegram_bot_token}/setWebhook"
    )
    try:
        response = requests.post(
            endpoint,
            json={
                "url": (
                    settings.backend_base_url.rstrip("/")
                    + "/webhooks/telegram"
                ),
                "secret_token": settings.telegram_webhook_secret,
                "allowed_updates": ["message", "edited_message"],
                "drop_pending_updates": False,
            },
            timeout=30,
        )
        response.raise_for_status()
        if not response.json().get("ok"):
            raise RuntimeError("Telegram rejected webhook registration.")
    except Exception:
        logger.exception("Telegram webhook registration failed")
    else:
        logger.info("Telegram webhook registered successfully")
