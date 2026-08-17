"""Durable per-recipient delivery for primary market-signal messages."""

from __future__ import annotations

import hashlib
from typing import Any, Callable, Iterable

from loguru import logger
from sqlalchemy import text

from core.database import session_scope


def _recipient_hash(recipient: str) -> str:
    return hashlib.sha256(recipient.encode("utf-8")).hexdigest()


def deliver_pending_signal_recipients(
    *,
    channel: str,
    recipients: Iterable[str],
    send: Callable[[str, str], Any],
    format_message: Callable[[dict[str, Any]], str],
    max_attempts: int = 3,
) -> tuple[int, int]:
    """Deliver fresh signals exactly once per channel recipient.

    The additive ``signal_channel_deliveries`` table is authoritative for
    recipient state. A successful recipient is never retried merely because a
    different recipient failed. Claims expire after five minutes so a crashed
    worker can safely retry. If the delivery table is unavailable, this helper
    fails closed and sends nothing.
    """
    clean_channel = str(channel or "").strip().lower()
    if clean_channel not in {"telegram", "whatsapp"}:
        raise ValueError("Unsupported signal delivery channel.")

    clean_recipients = list(
        dict.fromkeys(str(value).strip() for value in recipients if str(value).strip())
    )
    if not clean_recipients:
        return 0, 0

    try:
        with session_scope() as session:
            rows = (
                session.execute(
                    text(
                        """
                        SELECT *
                        FROM public.market_signals
                        WHERE signal_type IN ('BUY', 'SELL')
                          AND signal_time >= NOW() - INTERVAL '6 hours'
                          AND signal_time <= NOW() + INTERVAL '5 minutes'
                          AND COALESCE(lifecycle_status, 'DRAFT') NOT IN (
                              'STOPPED', 'CLOSED', 'CANCELLED',
                              'EXPIRED', 'TRASHED'
                          )
                        ORDER BY signal_time
                        LIMIT 20
                        """
                    )
                )
                .mappings()
                .all()
            )
    except Exception as exc:
        logger.warning(
            "Primary signal delivery lookup failed closed: channel={} category={}",
            clean_channel,
            exc.__class__.__name__,
        )
        return 0, 0

    delivered = 0
    failed = 0
    for raw_signal in rows:
        signal = dict(raw_signal)
        message = format_message(signal)

        for recipient in clean_recipients:
            recipient_hash = _recipient_hash(recipient)
            try:
                with session_scope() as session:
                    session.execute(
                        text(
                            """
                            INSERT INTO public.signal_channel_deliveries (
                                signal_id, channel, recipient_hash
                            ) VALUES (
                                :signal_id, :channel, :recipient_hash
                            )
                            ON CONFLICT (signal_id, channel, recipient_hash)
                            DO NOTHING
                            """
                        ),
                        {
                            "signal_id": signal["id"],
                            "channel": clean_channel,
                            "recipient_hash": recipient_hash,
                        },
                    )
                    claim = (
                        session.execute(
                            text(
                                """
                                UPDATE public.signal_channel_deliveries
                                SET claimed_at = NOW(),
                                    attempts = attempts + 1,
                                    error_category = NULL,
                                    updated_at = NOW()
                                WHERE signal_id = :signal_id
                                  AND channel = :channel
                                  AND recipient_hash = :recipient_hash
                                  AND sent_at IS NULL
                                  AND attempts < :max_attempts
                                  AND (
                                      claimed_at IS NULL
                                      OR claimed_at < NOW() - INTERVAL '5 minutes'
                                  )
                                RETURNING id
                                """
                            ),
                            {
                                "signal_id": signal["id"],
                                "channel": clean_channel,
                                "recipient_hash": recipient_hash,
                                "max_attempts": int(max_attempts),
                            },
                        )
                        .mappings()
                        .first()
                    )
            except Exception as exc:
                logger.warning(
                    "Primary signal delivery claim failed closed: channel={} "
                    "signal_id={} category={}",
                    clean_channel,
                    signal.get("id"),
                    exc.__class__.__name__,
                )
                continue

            if claim is None:
                continue

            external_message_id: str | None = None
            error_category: str | None = None
            try:
                result = send(recipient, message)
                if result not in (None, ""):
                    external_message_id = str(result)[:512]
            except Exception as exc:
                error_category = exc.__class__.__name__
                failed += 1
                logger.warning(
                    "Primary signal delivery failed: channel={} signal_id={} "
                    "category={}",
                    clean_channel,
                    signal.get("id"),
                    error_category,
                )

            sent = error_category is None
            try:
                with session_scope() as session:
                    session.execute(
                        text(
                            """
                            UPDATE public.signal_channel_deliveries
                            SET sent_at = CASE WHEN :sent THEN NOW() ELSE sent_at END,
                                external_message_id = CASE
                                    WHEN :sent THEN :external_message_id
                                    ELSE external_message_id
                                END,
                                claimed_at = CASE WHEN :sent THEN claimed_at ELSE NULL END,
                                error_category = :error_category,
                                updated_at = NOW()
                            WHERE id = :delivery_id
                            """
                        ),
                        {
                            "delivery_id": claim["id"],
                            "sent": sent,
                            "external_message_id": external_message_id,
                            "error_category": error_category,
                        },
                    )

                    if sent:
                        legacy_column = (
                            "whatsapp_sent_at"
                            if clean_channel == "whatsapp"
                            else "telegram_sent_at"
                        )
                        session.execute(
                            text(
                                f"""
                                UPDATE public.market_signals
                                SET {legacy_column} = COALESCE({legacy_column}, NOW()),
                                    updated_at = NOW()
                                WHERE id = :signal_id
                                  AND NOT EXISTS (
                                      SELECT 1
                                      FROM public.signal_channel_deliveries d
                                      WHERE d.signal_id = :signal_id
                                        AND d.channel = :channel
                                        AND d.sent_at IS NULL
                                  )
                                """
                            ),
                            {
                                "signal_id": signal["id"],
                                "channel": clean_channel,
                            },
                        )
            except Exception as exc:
                logger.error(
                    "Primary signal delivery finalization failed: channel={} "
                    "signal_id={} category={}",
                    clean_channel,
                    signal.get("id"),
                    exc.__class__.__name__,
                )
                continue

            if sent:
                delivered += 1

    return delivered, failed
