"""Canonical Captain/Shadow audit and Master AI explanation service."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import json
from typing import Any
from uuid import uuid4

from loguru import logger
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from core.database import session_scope
from services.captain_ai_runtime import CaptainObservedRun


_ALLOWED_SOURCES = {"ADMIN", "TELEGRAM", "SIGNAL_AGENT", "SHADOW_API"}


@dataclass(frozen=True)
class CaptainShadowAuditResult:
    correlation_id: str
    persisted: bool
    master_ai_summary: str


def _decimal(value: Decimal | None) -> str:
    return "—" if value is None else str(value)


def build_master_ai_summary(
    observed: CaptainObservedRun,
    *,
    shadow_status: str,
    shadow_reason: str | None = None,
    telegram_delivered: bool | None = None,
    whatsapp_delivered: bool | None = None,
) -> str:
    """Build a deterministic explanation from the verified Captain run only."""
    assessment = observed.assessment
    reasons = [str(value).strip() for value in assessment.reasons if str(value).strip()]
    reason_text = "; ".join(reasons[:3]) or "No additional Captain reason."
    parts = [
        f"Captain: {assessment.decision.value} {assessment.direction.value}",
        f"confidence={int(assessment.confidence)}%",
        f"CMP={_decimal(observed.live_cmp)}",
        f"high={_decimal(observed.day_high)}",
        f"low={_decimal(observed.day_low)}",
        f"Shadow={str(shadow_status).upper()}",
    ]
    if shadow_reason:
        parts.append(f"shadow_reason={str(shadow_reason).strip()[:300]}")
    if telegram_delivered is not None:
        parts.append(f"telegram={'DELIVERED' if telegram_delivered else 'NOT_DELIVERED'}")
    if whatsapp_delivered is not None:
        parts.append(f"whatsapp={'DELIVERED' if whatsapp_delivered else 'NOT_DELIVERED'}")
    parts.append(f"Reason: {reason_text}")
    return " | ".join(parts)


def record_captain_shadow_audit(
    observed: CaptainObservedRun,
    *,
    source_interface: str,
    shadow_status: str,
    shadow_reason: str | None = None,
    signal_id: int | None = None,
    telegram_delivered: bool | None = None,
    whatsapp_delivered: bool | None = None,
    correlation_id: str | None = None,
) -> CaptainShadowAuditResult:
    """Persist one shared audit row without changing trading/delivery decisions.

    Audit persistence is observability-only. If the additive migration is not
    available yet, the caller still receives the deterministic verified summary
    while the write is reported as not persisted.
    """
    source = str(source_interface or "").strip().upper()
    if source not in _ALLOWED_SOURCES:
        raise ValueError("Unsupported Captain/Shadow audit source interface.")

    correlation = str(correlation_id or uuid4().hex)[:128]
    summary = build_master_ai_summary(
        observed,
        shadow_status=shadow_status,
        shadow_reason=shadow_reason,
        telegram_delivered=telegram_delivered,
        whatsapp_delivered=whatsapp_delivered,
    )
    assessment = observed.assessment

    try:
        with session_scope() as session:
            session.execute(
                text(
                    """
                    INSERT INTO public.captain_shadow_audits (
                        correlation_id, source_interface, signal_id,
                        signal_date, market_source, day_high, day_low, live_cmp,
                        buy_base, sell_base, captain_decision, captain_direction,
                        captain_confidence, captain_reasons, shadow_status,
                        shadow_reason, signal_generated, delivery_started,
                        telegram_delivered, whatsapp_delivered, master_ai_summary
                    ) VALUES (
                        :correlation_id, :source_interface, :signal_id,
                        :signal_date, :market_source, :day_high, :day_low, :live_cmp,
                        :buy_base, :sell_base, :captain_decision, :captain_direction,
                        :captain_confidence, CAST(:captain_reasons AS JSONB), :shadow_status,
                        :shadow_reason, :signal_generated, :delivery_started,
                        :telegram_delivered, :whatsapp_delivered, :master_ai_summary
                    )
                    ON CONFLICT (correlation_id) DO NOTHING
                    """
                ),
                {
                    "correlation_id": correlation,
                    "source_interface": source,
                    "signal_id": signal_id,
                    "signal_date": observed.signal_date,
                    "market_source": observed.source,
                    "day_high": observed.day_high,
                    "day_low": observed.day_low,
                    "live_cmp": observed.live_cmp,
                    "buy_base": observed.buy_base,
                    "sell_base": observed.sell_base,
                    "captain_decision": assessment.decision.value,
                    "captain_direction": assessment.direction.value,
                    "captain_confidence": int(assessment.confidence),
                    "captain_reasons": json.dumps(list(assessment.reasons)),
                    "shadow_status": str(shadow_status or "UNKNOWN").upper()[:64],
                    "shadow_reason": str(shadow_reason)[:1000] if shadow_reason else None,
                    "signal_generated": bool(assessment.signal_generated),
                    "delivery_started": bool(assessment.delivery_started),
                    "telegram_delivered": telegram_delivered,
                    "whatsapp_delivered": whatsapp_delivered,
                    "master_ai_summary": summary[:4000],
                },
            )
    except ProgrammingError as exc:
        original = getattr(exc, "orig", None)
        if getattr(original, "sqlstate", None) == "42P01":
            logger.warning("Captain/Shadow audit migration unavailable; audit write skipped")
            return CaptainShadowAuditResult(correlation, False, summary)
        raise

    return CaptainShadowAuditResult(correlation, True, summary)


def latest_captain_shadow_audit() -> dict[str, Any] | None:
    """Return the latest canonical audit for Admin/Telegram Master AI display."""
    try:
        with session_scope() as session:
            row = (
                session.execute(
                    text(
                        """
                        SELECT correlation_id, source_interface, signal_id,
                               signal_date, market_source, day_high, day_low,
                               live_cmp, buy_base, sell_base, captain_decision,
                               captain_direction, captain_confidence, captain_reasons,
                               shadow_status, shadow_reason, signal_generated,
                               delivery_started, telegram_delivered,
                               whatsapp_delivered, master_ai_summary, created_at
                        FROM public.captain_shadow_audits
                        ORDER BY created_at DESC, id DESC
                        LIMIT 1
                        """
                    )
                )
                .mappings()
                .first()
            )
    except ProgrammingError as exc:
        original = getattr(exc, "orig", None)
        if getattr(original, "sqlstate", None) == "42P01":
            return None
        raise
    return dict(row) if row else None
