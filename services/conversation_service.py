"""Conversation persistence, inbound deduplication, and human takeover."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text

from config import get_settings
from core.database import session_scope
from services.job_queue import enqueue_agent_job
from services.telegram_service import TelegramService
from services.whatsapp_service import WhatsAppService


def record_inbound_message(
    *,
    channel: str,
    external_user_id: str,
    external_message_id: str,
    body: str,
    media: dict[str, Any] | None = None,
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


def send_human_reply(
    conversation_id: int,
    admin_id: int,
    message: str,
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
    return external_id


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
