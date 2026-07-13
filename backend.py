"""FastAPI webhook backend for production Telegram and WhatsApp events."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from contextlib import asynccontextmanager
import traceback
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query, Request, Response
from loguru import logger
import requests
from sqlalchemy import text

from config import get_settings
from core.database import session_scope
from services.conversation_service import record_inbound_message
from services.content_service import list_categories, list_content
from services.migration_service import apply_pending_migrations
from services.public_market_service import get_live_market_signals
from services.telegram_master_ai_control import is_master_command
from services.telegram_master_ai_webhook import (
    handle_master_telegram_webhook,
)
from services.telegram_service import TelegramService
from services.url_service import public_api_base_url


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Start the API even when optional startup tasks are temporarily degraded."""
    try:
        apply_pending_migrations()
    except Exception:
        logger.exception("Startup migrations failed; API will remain online.")
    try:
        # Warm the schema cache once so public detail requests stay within the
        # frontend's strict two-second network budget.
        list_content(public_only=True, limit=1)
    except Exception:
        logger.exception("Public content cache warmup failed; API will remain online.")
    try:
        _configure_telegram_webhook()
    except Exception:
        logger.exception("Telegram webhook startup configuration failed")
    yield


app = FastAPI(
    title="AI Market Analytics Pro Backend",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)


def _search_indexing_blocked() -> bool:
    """Return crawl-block flag without making health checks depend on settings."""
    raw = os.getenv("BLOCK_SEARCH_INDEXING", "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    try:
        return bool(get_settings().block_search_indexing)
    except Exception:
        return False


def _blocked_robots_txt() -> str:
    """Return conservative crawler rules for pre-launch/private migration mode."""
    return (
        "User-agent: *\n"
        "Disallow: /\n"
        "X-Robots-Tag: noindex, nofollow, noarchive\n"
    )


@app.middleware("http")
async def add_search_indexing_headers(request: Request, call_next: Any) -> Response:
    """Prevent accidental indexing when the deployment is in private mode."""
    response = await call_next(request)
    if _search_indexing_blocked():
        response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    return response


@app.get("/health")
def health() -> dict[str, str]:
    """Return lightweight liveness for Railway network health checks."""
    return {"status": "healthy"}


@app.get("/ready")
def ready() -> dict[str, str]:
    """Return database readiness without exposing configuration details."""
    with session_scope() as session:
        session.execute(text("SELECT 1"))
    return {"status": "ready", "database": "ok"}


@app.get("/sitemap.xml")
def sitemap() -> Response:
    """Serve the latest SEO-agent generated sitemap."""
    if _search_indexing_blocked():
        empty_sitemap = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" />'
        )
        return Response(empty_sitemap, media_type="application/xml")
    return Response(_public_setting("SEO_SITEMAP_XML"), media_type="application/xml")


@app.get("/robots.txt")
def robots() -> Response:
    """Serve the latest SEO-agent generated crawler rules."""
    if _search_indexing_blocked():
        return Response(_blocked_robots_txt(), media_type="text/plain")
    return Response(_public_setting("SEO_ROBOTS_TXT"), media_type="text/plain")


PUBLIC_CONTENT_TYPES = {
    "BLOG",
    "AI_BLOG",
    "ADVISORY",
    "ANALYSIS",
    "EDUCATION",
    "ANNOUNCEMENT",
    "PAGE",
    "SIGNAL_POST",
}


@app.get("/public/categories")
def public_categories() -> dict[str, Any]:
    """Return public category navigation for the lightweight website."""
    return {"items": list_categories(public_only=True)}


@app.get("/public/content")
def public_content(
    content_type: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    """Return published public content without exposing admin-only rows."""
    normalized_type = str(content_type or "").strip().upper() or None
    if normalized_type and normalized_type not in PUBLIC_CONTENT_TYPES:
        raise HTTPException(400, "Unsupported public content type.")
    return {
        "items": list_content(
            content_type=normalized_type,
            public_only=True,
            limit=limit,
        )
    }


@app.get("/public/content/{slug}")
def public_content_detail(slug: str) -> dict[str, Any]:
    """Return one published item by slug for crawlable public detail pages."""
    normalized_slug = str(slug or "").strip()
    if not normalized_slug:
        raise HTTPException(404, "Public content not found.")
    rows = list_content(
        public_only=True,
        limit=1,
        exact_slug=normalized_slug,
    )
    item = rows[0] if rows else None
    if item is None:
        raise HTTPException(404, "Public content not found.")
    return {"item": item}


@app.get("/public/signals")
def public_signals(
    limit: int = Query(default=12, ge=1, le=50),
) -> dict[str, Any]:
    """Return the latest public signal rows without caching stale targets."""
    return {"items": get_live_market_signals(limit=limit)}



@app.post("/webhooks/telegram/master")
async def telegram_master_ai_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(
        default=None,
        alias="X-Telegram-Bot-Api-Secret-Token",
    ),
) -> dict[str, Any]:
    """Receive Master AI Telegram bot updates."""
    expected = get_settings().telegram_webhook_secret
    if not expected:
        raise HTTPException(503, "Telegram webhook is not configured.")
    if not _telegram_webhook_secret_matches(
        x_telegram_bot_api_secret_token,
        expected,
    ):
        logger.warning(
            "Master Telegram webhook rejected: missing or mismatched secret header"
        )
        raise HTTPException(403, "Invalid webhook signature.")

    payload = await request.json()
    return handle_master_telegram_webhook(payload)


@app.post("/webhooks/telegram")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(
        default=None,
        alias="X-Telegram-Bot-Api-Secret-Token",
    ),
) -> dict[str, bool]:
    """Validate Telegram webhook secret and queue inbound messages."""
    expected = get_settings().telegram_webhook_secret
    if not expected:
        raise HTTPException(503, "Telegram webhook is not configured.")
    if not _telegram_webhook_secret_matches(
        x_telegram_bot_api_secret_token,
        expected,
    ):
        logger.warning(
            "Telegram webhook rejected: missing or mismatched secret header"
        )
        raise HTTPException(403, "Invalid webhook signature.")
    payload = await request.json()

    if _should_route_generic_telegram_update_to_master(payload):
        handle_master_telegram_webhook(payload)
        return {"accepted": True}

    message = payload.get("message") or payload.get("edited_message")
    if not message or message.get("from", {}).get("is_bot"):
        return {"accepted": True}
    text_body = message.get("text") or message.get("caption") or ""
    if _is_telegram_command(text_body, "trend"):
        try:
            TelegramService().send_latest_trend(str(message["chat"]["id"]))
        except Exception as exc:
            internal_traceback = traceback.format_exc()
            logger.exception("Telegram /trend webhook command failed")
            TelegramService.record_internal_error(
                "telegram_reply_agent",
                exc,
                internal_traceback,
            )
            try:
                TelegramService().send_text(
                    str(message["chat"]["id"]),
                    TelegramService.SAFE_USER_ERROR,
                )
            except Exception:
                logger.exception("Telegram safe fallback delivery failed")
        return {"accepted": True}
    media = _telegram_media(message)
    record_inbound_message(
        channel="TELEGRAM",
        external_user_id=str(message["chat"]["id"]),
        external_message_id=str(message["message_id"]),
        body=text_body or f"[{media.get('type', 'media')}]",
        media=media,
    )
    return {"accepted": True}


def _should_route_generic_telegram_update_to_master(
    payload: dict[str, Any],
) -> bool:
    """Route Master AI commands even if Telegram points at the generic webhook."""
    message = payload.get("message") or payload.get("edited_message")
    if not isinstance(message, dict):
        return False
    text_body = str(message.get("text") or message.get("caption") or "").strip()
    if not text_body:
        return False
    if is_master_command(text_body):
        return True
    lowered = text_body.lower()
    return any(
        marker in lowered
        for marker in (
            "seo blog",
            "blog banao",
            "blog banaiye",
            "article banao",
            "post banao",
            "website par blog",
        )
    )


def _is_telegram_command(text_body: str, command: str) -> bool:
    """Match a Telegram command with or without the bot username suffix."""
    first_token = str(text_body or "").strip().split(maxsplit=1)[0].lower()
    if not first_token.startswith("/"):
        return False
    command_name = first_token[1:].split("@", maxsplit=1)[0]
    return command_name == command.lower()


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

    public_api_url = public_api_base_url(settings)

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

    telegram_url = f"https://api.telegram.org/bot{token}/setWebhook"

    try:
        response = requests.post(
            telegram_url,
            json=_telegram_webhook_payload(
                public_api_url,
                webhook_secret,
                path=path,
            ),
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


def _telegram_webhook_secret_matches(
    provided: str | None,
    expected: str,
) -> bool:
    """Compare Telegram webhook secrets without exposing either value."""
    normalized_expected = str(expected or "").strip()
    normalized_provided = str(provided or "").strip()
    if not normalized_expected or not normalized_provided:
        return False
    return hmac.compare_digest(normalized_provided, normalized_expected)


def _telegram_webhook_payload(
    backend_base_url: str,
    webhook_secret: str,
    *,
    path: str = "/webhooks/telegram",
) -> dict[str, Any]:
    """Build the Telegram setWebhook payload from environment values only."""
    return {
        "url": backend_base_url.rstrip("/") + path,
        "secret_token": webhook_secret.strip(),
        "allowed_updates": ["message", "edited_message"],
        "drop_pending_updates": False,
    }
