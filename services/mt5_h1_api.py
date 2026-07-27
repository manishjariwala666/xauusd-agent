"""FastAPI routes for signed MT5 XAUUSD H1 market-data ingestion."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Header, HTTPException, Request
from loguru import logger

from services.mt5_h1_market_data import (
    MT5H1AuthenticationError,
    MT5H1DuplicateError,
    MT5H1ValidationError,
    ingest_h1_payload,
    sheet_response,
)
from services.mt5_h1_repository import H1Candle
from services.mt5_h1_repository_factory import build_mt5_h1_repository
from services.mt5_h1_rate_limit import MT5RateLimiter


router = APIRouter(prefix="/market-data/mt5", tags=["mt5-h1"])
repository = build_mt5_h1_repository()
rate_limiter = MT5RateLimiter(max_requests=30)

MAX_FRESH_AGE = timedelta(minutes=10)


def _secret() -> str:
    return os.getenv("MT5_H1_INGEST_SECRET", "").strip()


def _age_seconds(candle: H1Candle, now: datetime | None = None) -> int:
    current = now or datetime.now(timezone.utc)
    received = candle.received_at_utc.astimezone(timezone.utc)
    return max(0, int((current - received).total_seconds()))


def _require_fresh_candle() -> H1Candle:
    candle = repository.latest_candle("XAUUSD")

    if candle is None:
        raise HTTPException(
            status_code=503,
            detail="MT5 H1 candle unavailable.",
        )

    if _age_seconds(candle) > int(MAX_FRESH_AGE.total_seconds()):
        raise HTTPException(
            status_code=503,
            detail="MT5 H1 candle is stale.",
        )

    return candle


@router.post("/h1")
async def ingest_mt5_h1(
    request: Request,
    x_mt5_signature: str | None = Header(default=None),
) -> dict[str, object]:
    client_key = request.client.host if request.client else "unknown"

    if not rate_limiter.allow(client_key):
        logger.warning(
            "MT5 H1 ingestion rate limited for client category={}",
            "known" if client_key != "unknown" else "unknown",
        )
        raise HTTPException(
            status_code=429,
            detail="MT5 ingestion rate limit exceeded.",
        )

    raw_body = await request.body()

    try:
        candle = ingest_h1_payload(
            raw_body=raw_body,
            signature=x_mt5_signature or "",
            secret=_secret(),
            repository=repository,
        )
    except MT5H1AuthenticationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except MT5H1DuplicateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except MT5H1ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    logger.info(
        "MT5 H1 candle accepted symbol={} timeframe={} source={}",
        candle.symbol,
        "H1",
        "MT5",
    )

    return {
        "status": "accepted",
        "symbol": candle.symbol,
        "timeframe": "H1",
        "candle_start_utc": candle.candle_start_utc.isoformat(),
        "source": "MT5",
    }


@router.get("/h1/latest")
def latest_mt5_h1() -> dict[str, object]:
    candle = _require_fresh_candle()
    return sheet_response(candle, fresh=True)


@router.get("/health")
def mt5_h1_health() -> dict[str, object]:
    candle = repository.latest_candle("XAUUSD")

    if candle is None:
        return {
            "status": "unavailable",
            "source": "MT5",
            "timeframe": "H1",
        }

    age_seconds = _age_seconds(candle)

    return {
        "status": (
            "healthy"
            if age_seconds <= int(MAX_FRESH_AGE.total_seconds())
            else "stale"
        ),
        "source": "MT5",
        "timeframe": "H1",
        "age_seconds": age_seconds,
        "candle_start_utc": candle.candle_start_utc.isoformat(),
    }
