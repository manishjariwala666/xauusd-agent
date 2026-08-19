"""Authenticated Captain AI shadow diagnostics and read-only status."""

from __future__ import annotations

from decimal import Decimal
import os
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Response
from loguru import logger

from services.admin_auth_api import _require_bff
from services.captain_ai_runtime import CaptainObservedRun, run_captain_observed
from services.captain_shadow_audit import record_captain_shadow_audit


router = APIRouter()


def _shadow_enabled() -> bool:
    return os.getenv("CAPTAIN_SIGNAL_SHADOW_GATE", "").strip().lower() in {
        "1", "true", "yes", "on",
    }


def _decimal(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _target_progress(observed: CaptainObservedRun) -> dict[str, Any]:
    """Verify canonical Sheet targets against the observed trading-day range."""
    high = observed.day_high
    low = observed.day_low
    buy = tuple(observed.buy_targets)
    sell = tuple(observed.sell_targets)
    completed_buy = tuple(value for value in buy if high is not None and high >= value)
    completed_sell = tuple(value for value in sell if low is not None and low <= value)
    return {
        "source": observed.source,
        "signal_date": observed.signal_date.isoformat(),
        "day_high": _decimal(high),
        "day_low": _decimal(low),
        "buy_base": _decimal(observed.buy_base),
        "sell_base": _decimal(observed.sell_base),
        "buy_targets": [_decimal(value) for value in buy],
        "sell_targets": [_decimal(value) for value in sell],
        "completed_buy_targets": [_decimal(value) for value in completed_buy],
        "completed_sell_targets": [_decimal(value) for value in completed_sell],
        "next_buy_target": _decimal(buy[len(completed_buy)]) if len(completed_buy) < len(buy) else None,
        "next_sell_target": _decimal(sell[len(completed_sell)]) if len(completed_sell) < len(sell) else None,
        "verification": "SHEET_RANGE_ONLY",
    }


def _assessment_payload(
    observed: CaptainObservedRun,
    *,
    audit_correlation_id: str | None = None,
    audit_persisted: bool | None = None,
    master_ai_summary: str | None = None,
) -> dict[str, Any]:
    result = observed.assessment
    weekly = result.weekly
    weekly_payload = None
    if weekly is not None:
        weekly_payload = {
            "trading_days": weekly.trading_days,
            "weekly_high": _decimal(weekly.weekly_high),
            "weekly_low": _decimal(weekly.weekly_low),
            "weekly_range": _decimal(weekly.weekly_range),
            "average_daily_range": _decimal(weekly.average_daily_range),
            "higher_highs": weekly.higher_highs,
            "lower_highs": weekly.lower_highs,
            "higher_lows": weekly.higher_lows,
            "lower_lows": weekly.lower_lows,
            "bias": weekly.bias,
        }

    return {
        "mode": "CAPTAIN_SHADOW",
        "decision": result.decision.value,
        "direction": result.direction.value,
        "confidence": int(result.confidence),
        "live_cmp": _decimal(result.live_cmp),
        "buy_base": _decimal(result.buy_base),
        "sell_base": _decimal(result.sell_base),
        "targets": [_decimal(value) for value in result.targets],
        "stop_loss": _decimal(result.stop_loss),
        "news_locked": bool(result.news_locked),
        "macro_bias": str(result.macro_bias),
        "macro_confidence": int(result.macro_confidence),
        "weekly": weekly_payload,
        "reasons": list(result.reasons),
        "read_only": bool(result.read_only),
        "signal_generated": bool(result.signal_generated),
        "delivery_started": bool(result.delivery_started),
        "observed_market": _target_progress(observed),
        "audit": {
            "correlation_id": audit_correlation_id,
            "persisted": audit_persisted,
        },
        "master_ai_summary": master_ai_summary,
    }


def _load_observed_status() -> CaptainObservedRun:
    try:
        return run_captain_observed()
    except Exception as exc:
        logger.warning(
            "Captain status assessment failed: type={}",
            type(exc).__name__,
        )
        raise HTTPException(503, "Captain status unavailable.") from None


@router.get("/internal/captain/status")
def captain_read_only_status(
    response: Response,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Return Captain/Sheet status without audit writes, signal creation or delivery."""
    _require_bff(x_admin_bff_key)
    response.headers["Cache-Control"] = "private, no-store"
    observed = _load_observed_status()
    payload = _assessment_payload(observed)
    payload["mode"] = "CAPTAIN_STATUS"
    payload["audit"] = {
        "correlation_id": None,
        "persisted": False,
    }
    payload["read_only"] = True
    payload["signal_generated"] = False
    payload["delivery_started"] = False
    return payload


@router.get("/internal/captain/shadow")
def captain_shadow_diagnostic(
    response: Response,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Run Captain assessment without creating or delivering a signal."""
    if not _shadow_enabled():
        raise HTTPException(404, "Not found.")
    _require_bff(x_admin_bff_key)
    response.headers["Cache-Control"] = "private, no-store"

    observed = _load_observed_status()
    decision = str(observed.assessment.decision.value).upper()
    shadow_status = "VERIFIED" if decision == "APPROVE" else "BLOCKED"
    shadow_reason = (
        str(observed.assessment.reasons[0])
        if observed.assessment.reasons
        else f"Captain decision is {decision}."
    )

    try:
        audit = record_captain_shadow_audit(
            observed,
            source_interface="SHADOW_API",
            shadow_status=shadow_status,
            shadow_reason=shadow_reason,
        )
    except Exception as exc:
        logger.warning(
            "Captain shadow diagnostic audit failed: type={}",
            type(exc).__name__,
        )
        audit = None

    return _assessment_payload(
        observed,
        audit_correlation_id=(audit.correlation_id if audit else None),
        audit_persisted=(audit.persisted if audit else False),
        master_ai_summary=(audit.master_ai_summary if audit else None),
    )
