"""Authenticated read-only Captain AI shadow diagnostics."""

from __future__ import annotations

from decimal import Decimal
import os
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Response
from loguru import logger

from services.admin_auth_api import _require_bff
from services.captain_ai_runtime import run_captain_read_only


router = APIRouter()


def _shadow_enabled() -> bool:
    return os.getenv(
        "CAPTAIN_SIGNAL_SHADOW_GATE",
        "",
    ).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _decimal(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _assessment_payload(result: Any) -> dict[str, Any]:
    weekly = result.weekly

    weekly_payload = None
    if weekly is not None:
        weekly_payload = {
            "trading_days": weekly.trading_days,
            "weekly_high": _decimal(weekly.weekly_high),
            "weekly_low": _decimal(weekly.weekly_low),
            "weekly_range": _decimal(weekly.weekly_range),
            "average_daily_range": _decimal(
                weekly.average_daily_range
            ),
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
        "targets": [
            _decimal(value)
            for value in result.targets
        ],
        "stop_loss": _decimal(result.stop_loss),
        "news_locked": bool(result.news_locked),
        "macro_bias": str(result.macro_bias),
        "macro_confidence": int(result.macro_confidence),
        "weekly": weekly_payload,
        "reasons": list(result.reasons),
        "read_only": bool(result.read_only),
        "signal_generated": bool(result.signal_generated),
        "delivery_started": bool(result.delivery_started),
    }


@router.get("/internal/captain/shadow")
def captain_shadow_diagnostic(
    response: Response,
    x_admin_bff_key: Annotated[
        str | None,
        Header(),
    ] = None,
) -> dict[str, Any]:
    """Run Captain assessment without creating or delivering a signal."""
    if not _shadow_enabled():
        raise HTTPException(404, "Not found.")

    _require_bff(x_admin_bff_key)

    response.headers["Cache-Control"] = "private, no-store"

    try:
        result = run_captain_read_only()
    except Exception:
        logger.exception(
            "Captain shadow diagnostic assessment failed"
        )
        raise HTTPException(
            503,
            "Captain shadow assessment unavailable.",
        ) from None

    return _assessment_payload(result)
