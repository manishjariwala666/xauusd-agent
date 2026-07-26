"""Conversation persistence, inbound deduplication, and human takeover."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import os
import re
from typing import Any, Callable

from loguru import logger
from sqlalchemy import text

from config import get_settings
from core.database import session_scope
from services.job_queue import enqueue_agent_job
from services.google_sheets_service import append_message_log
from services.telegram_service import TelegramService
from services.whatsapp_service import WhatsAppService
from services.whatsapp_standing_authorization import (
    AutomationDecisionStatus,
    WhatsAppStandingAuthorizationService,
    classify_inbound_action,
)


def record_inbound_message(
    *,
    channel: str,
    external_user_id: str,
    external_message_id: str,
    body: str,
    media: dict[str, Any] | None = None,
    channel_identity: str | None = None,
    authorization_service: WhatsAppStandingAuthorizationService | None = None,
    enqueue_job: Callable[..., int] | None = None,
) -> tuple[int, bool]:
    """Persist one inbound message and enqueue an AI reply exactly once."""
    normalized_channel = channel.upper()
    if normalized_channel not in {"TELEGRAM", "WHATSAPP"}:
        raise ValueError("Unsupported conversation channel.")
    with session_scope() as session:
        conversation_id = session.execute(
            text(
                """
                INSERT INTO public.ai_conversations (
                    channel, external_user_id, last_message_at
                ) VALUES (:channel, :external_user_id, NOW())
                ON CONFLICT (channel, external_user_id) DO UPDATE
                SET last_message_at = NOW(), updated_at = NOW()
                RETURNING id
                """
            ),
            {
                "channel": normalized_channel,
                "external_user_id": external_user_id,
            },
        ).scalar_one()
        inserted = session.execute(
            text(
                """
                INSERT INTO public.ai_messages (
                    conversation_id, sender_type, body,
                    external_message_id, media
                ) VALUES (
                    :conversation_id, 'USER', :body,
                    :external_message_id, CAST(:media AS JSONB)
                )
                ON CONFLICT (conversation_id, external_message_id) DO NOTHING
                RETURNING id
                """
            ),
            {
                "conversation_id": conversation_id,
                "body": body[:10000],
                "external_message_id": external_message_id,
                "media": __import__("json").dumps(media or {}),
            },
        ).scalar_one_or_none()
    if inserted is None:
        return int(conversation_id), False
    log_identity = (
        _whatsapp_log_reference(external_user_id)
        if normalized_channel == "WHATSAPP"
        else external_user_id
    )
    append_message_log(
        channel=normalized_channel,
        status="inbound",
        user_id=log_identity,
        phone=log_identity if normalized_channel == "WHATSAPP" else "",
        message=(
            "Inbound message stored in protected conversation history."
            if normalized_channel == "WHATSAPP"
            else body[:1000]
        ),
        notes=f"conversation_id={conversation_id}",
    )
    if (
        normalized_channel == "TELEGRAM"
        and _public_blog_commands_enabled()
        and _is_blog_only_command(body)
    ):
        enqueue_agent_job(
            "ai_blog_agent",
            {
                "topic": _extract_blog_topic(body),
                "publish": True,
                "include_image": _requests_image(body),
            },
        )
    elif normalized_channel == "WHATSAPP" and _auto_reply_agents_enabled():
        _authorize_and_enqueue_whatsapp_reply(
            conversation_id=int(conversation_id),
            channel_identity=str(channel_identity or ""),
            client_identity=external_user_id,
            external_message_id=external_message_id,
            body=body,
            authorization_service=authorization_service,
            enqueue_job=enqueue_job,
        )
    elif _auto_reply_agents_enabled():
        agent_key = (
            "telegram_reply_agent"
            if normalized_channel == "TELEGRAM"
            else "whatsapp_reply_agent"
        )
        enqueue_agent_job(
            agent_key,
            {"conversation_id": int(conversation_id)},
        )
    return int(conversation_id), True


def _authorize_and_enqueue_whatsapp_reply(
    *,
    conversation_id: int,
    channel_identity: str,
    client_identity: str,
    external_message_id: str,
    body: str,
    authorization_service: WhatsAppStandingAuthorizationService | None,
    enqueue_job: Callable[..., int] | None,
) -> AutomationDecisionStatus:
    """Fail closed unless a routine action has durable standing authorization."""
    if not channel_identity:
        logger.warning(
            "WhatsApp automation blocked: verified channel identity is missing."
        )
        return AutomationDecisionStatus.BLOCKED
    action = classify_inbound_action(body)
    try:
        standing = authorization_service or _whatsapp_authorization_service()
        webhook_decision = standing.claim_webhook(
            channel_identity=channel_identity,
            webhook_id=external_message_id,
        )
        if webhook_decision.status == AutomationDecisionStatus.DUPLICATE_IGNORED:
            return webhook_decision.status
        decision = standing.evaluate(
            channel_identity=channel_identity,
            client_identity=client_identity,
            action=action,
        )
    except Exception as exc:
        logger.warning(
            "WhatsApp automation blocked: authorization storage unavailable ({})",
            exc.__class__.__name__,
        )
        return AutomationDecisionStatus.BLOCKED
    if not decision.allowed:
        logger.info(
            "WhatsApp automation not queued: status={} action={}",
            decision.status.value,
            action,
        )
        return decision.status
    queue = enqueue_job or enqueue_agent_job
    queue(
        "whatsapp_reply_agent",
        {
            "conversation_id": conversation_id,
            "channel_identity": channel_identity,
            "client_identity": client_identity,
            "automation_action": action,
            "inbound_message_id": external_message_id,
            "delivery_idempotency_key": _delivery_idempotency_key(
                channel_identity, external_message_id
            ),
        },
    )
    return AutomationDecisionStatus.ALLOWED


def _auto_reply_agents_enabled() -> bool:
    """Keep public reply agents command-controlled unless explicitly enabled."""
    value = os.getenv("ENABLE_AUTO_REPLY_AGENTS", "false")
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _public_blog_commands_enabled() -> bool:
    """Keep public Telegram natural blog commands off by default."""
    value = os.getenv("ENABLE_PUBLIC_BLOG_COMMANDS", "false")
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def send_human_reply(
    conversation_id: int,
    admin_id: int,
    message: str,
    *,
    authorization_service: WhatsAppStandingAuthorizationService | None = None,
    channel_identity: str | None = None,
) -> str:
    """Send an admin response and immediately pause AI for the conversation."""
    if not message.strip():
        raise ValueError("Reply message is required.")
    with session_scope() as session:
        conversation = (
            session.execute(
                text(
                    """
                    SELECT channel, external_user_id
                    FROM public.ai_conversations WHERE id = :id
                    """
                ),
                {"id": conversation_id},
            )
            .mappings()
            .one()
        )
    if conversation["channel"] == "TELEGRAM":
        external_id = TelegramService().send_text(
            str(conversation["external_user_id"]), message
        )
    else:
        standing = authorization_service or _whatsapp_authorization_service()
        verified_channel = channel_identity or _configured_whatsapp_channel()
        if not verified_channel:
            raise RuntimeError(
                "Verified WhatsApp channel identity is not configured."
            )
        standing.record_owner_manual_reply(
            actor_id=str(admin_id),
            channel_identity=verified_channel,
            client_identity=str(conversation["external_user_id"]),
            conversation_reference=str(conversation_id),
        )
        external_id = WhatsAppService().send_text(
            str(conversation["external_user_id"]), message
        )
    takeover_until = datetime.now(timezone.utc) + timedelta(
        minutes=get_settings().human_takeover_minutes
    )
    with session_scope() as session:
        session.execute(
            text(
                """
                UPDATE public.ai_conversations
                SET human_takeover_until = :until, updated_at = NOW()
                WHERE id = :id
                """
            ),
            {"until": takeover_until, "id": conversation_id},
        )
        session.execute(
            text(
                """
                INSERT INTO public.ai_messages (
                    conversation_id, sender_type, body,
                    external_message_id, admin_user_id
                ) VALUES (:id, 'ADMIN', :body, :external_id, :admin_id)
                """
            ),
            {
                "id": conversation_id,
                "body": message,
                "external_id": external_id,
                "admin_id": admin_id,
            },
        )
    append_message_log(
        channel=str(conversation["channel"]),
        status="admin_reply",
        user_id=(
            _whatsapp_log_reference(str(conversation["external_user_id"]))
            if conversation["channel"] == "WHATSAPP"
            else str(conversation["external_user_id"])
        ),
        phone=(
            _whatsapp_log_reference(str(conversation["external_user_id"]))
            if conversation["channel"] == "WHATSAPP"
            else ""
        ),
        reply=(
            "Manual admin reply stored in protected conversation history."
            if conversation["channel"] == "WHATSAPP"
            else message[:1000]
        ),
        notes=f"conversation_id={conversation_id} admin_id={admin_id}",
    )
    return external_id


def record_verified_owner_whatsapp_reply(
    *,
    provider_owner_identity: str,
    channel_identity: str,
    client_identity: str,
    conversation_reference: str,
    resolve_verified_admin: Callable[[str, str], str | None],
    authorization_service: WhatsAppStandingAuthorizationService | None = None,
) -> bool:
    """Pause one client only after a server-side owner mapping succeeds."""
    actor_id = resolve_verified_admin(
        channel_identity, provider_owner_identity
    )
    if not actor_id:
        raise PermissionError("Verified owner mapping is required.")
    standing = authorization_service or _whatsapp_authorization_service()
    standing.record_owner_manual_reply(
        actor_id=str(actor_id),
        channel_identity=channel_identity,
        client_identity=client_identity,
        conversation_reference=conversation_reference,
    )
    return True


def _whatsapp_authorization_service() -> WhatsAppStandingAuthorizationService:
    from services.whatsapp_standing_authorization_repository import (
        build_postgres_standing_authorization_service,
    )

    return build_postgres_standing_authorization_service()


def _configured_whatsapp_channel() -> str:
    settings = get_settings()
    return str(
        settings.whatsapp_business_account_id
        or settings.whatsapp_phone_number_id
        or ""
    ).strip()


def _delivery_idempotency_key(
    channel_identity: str, external_message_id: str
) -> str:
    digest = hashlib.sha256(
        f"{channel_identity}:{external_message_id}:reply".encode("utf-8")
    ).hexdigest()
    return f"whatsapp-reply-{digest}"


def _whatsapp_log_reference(identity: str) -> str:
    return "wa_" + hashlib.sha256(
        str(identity or "").encode("utf-8")
    ).hexdigest()[:16]


def list_conversations(limit: int = 100) -> list[dict[str, Any]]:
    """Return recent conversations for protected admin tooling."""
    with session_scope() as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT c.id, c.channel, c.external_user_id,
                           c.human_takeover_until, c.last_message_at,
                           (SELECT body FROM public.ai_messages m
                            WHERE m.conversation_id = c.id
                            ORDER BY m.created_at DESC LIMIT 1) last_message
                    FROM public.ai_conversations c
                    ORDER BY c.last_message_at DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            )
            .mappings()
            .all()
        )
    return [dict(row) for row in rows]


def _is_blog_only_command(body: str) -> bool:
    """Detect natural-language Telegram requests that should create a blog."""
    normalized = _normalize_command_text(body)
    if not normalized:
        return False
    has_blog_intent = any(
        phrase in normalized
        for phrase in (
            "blog banao",
            "blog bana",
            "seo blog",
            "article banao",
            "article bana",
            "post banao",
            "post bana",
        )
    )
    if not has_blog_intent:
        return False
    signal_terms = {"signal", "buy sell", "buy/sell", "target signal"}
    return not any(term in normalized for term in signal_terms)


def _extract_blog_topic(body: str) -> str:
    """Keep the user's topic while removing command filler words."""
    topic = _normalize_command_text(body)
    removals = (
        "seo blog banao",
        "seo blog bana",
        "blog banao",
        "blog bana",
        "article banao",
        "article bana",
        "post banao",
        "post bana",
        "please",
        "pls",
        "krdo",
        "kardo",
        "kar do",
        " ka ",
        "banao",
        "bana",
    )
    for phrase in removals:
        topic = topic.replace(phrase, " ")
    topic = re.sub(r"\s+", " ", topic).strip(" -:,")
    return topic or "XAUUSD USA market analysis"


def _requests_image(body: str) -> bool:
    """Return whether the admin explicitly asked for image generation too."""
    normalized = _normalize_command_text(body)
    return any(
        term in normalized
        for term in (
            "image",
            "photo",
            "thumbnail",
            "banner",
            "campaign",
        )
    )


def _normalize_command_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").lower()).strip()
