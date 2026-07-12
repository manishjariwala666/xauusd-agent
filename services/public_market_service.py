"""Cached public XAUUSD and cryptocurrency market snapshot service."""

from __future__ import annotations

from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from threading import Lock
import time
from typing import Any

from loguru import logger
import requests
from sqlalchemy import text

from core.database import session_scope


@dataclass(frozen=True)
class CryptoQuote:
    symbol: str
    name: str
    price_usd: float
    change_24h: float


_cache_lock = Lock()
_crypto_cache: tuple[float, list[CryptoQuote]] = (0.0, [])


def get_xauusd_snapshot(supabase: Any) -> dict[str, Any] | None:
    """Return a public-safe XAUUSD snapshot without blocking page render.

    The public website should be lightweight. Reading the latest persisted
    signal is fast and avoids waiting on live market-provider APIs during page
    load. Worker/API jobs still use ``MarketDataService`` for fresh provider
    fetches before writing new signals.
    """
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(_latest_persisted_xauusd_snapshot)
    try:
        return future.result(timeout=1.5)
    except TimeoutError:
        logger.warning("Persisted XAUUSD snapshot timed out for public page")
        future.cancel()
        return None
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def _latest_persisted_xauusd_snapshot() -> dict[str, Any] | None:
    """Read the latest stored XAUUSD price from ``market_signals``."""
    try:
        with session_scope() as session:
            row = (
                session.execute(
                    text(
                        """
                        SELECT symbol, price, signal_time, updated_at, source
                        FROM public.market_signals
                        WHERE symbol IN ('XAUUSD', 'GC=F', 'XAU/USD')
                          AND price IS NOT NULL
                        ORDER BY signal_time DESC NULLS LAST,
                                 updated_at DESC NULLS LAST,
                                 id DESC
                        LIMIT 1
                        """
                    )
                )
                .mappings()
                .first()
            )
    except Exception:
        logger.exception("Persisted XAUUSD snapshot loading failed")
        return None

    if not row:
        return None
    return {
        "symbol": row.get("symbol") or "XAUUSD",
        "price": float(row["price"]),
        "observed_at": row.get("signal_time") or row.get("updated_at"),
        "source": row.get("source") or "DATABASE:market_signals",
    }


def get_top_crypto_gainers(limit: int = 20) -> list[CryptoQuote]:
    """Return top positive 24-hour movers from liquid market-cap assets."""
    global _crypto_cache
    now = time.monotonic()
    with _cache_lock:
        cached_at, cached_quotes = _crypto_cache
        if cached_quotes and now - cached_at < 60:
            return cached_quotes[:limit]

    try:
        response = requests.get(
            "https://api.coingecko.com/api/v3/coins/markets",
            params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": 100,
                "page": 1,
                "sparkline": "false",
                "price_change_percentage": "24h",
            },
            timeout=2,
        )
        response.raise_for_status()
        payload = response.json()
        quotes = [
            CryptoQuote(
                symbol=str(item["symbol"]).upper(),
                name=str(item["name"]),
                price_usd=float(item["current_price"]),
                change_24h=float(item["price_change_percentage_24h"]),
            )
            for item in payload
            if item.get("current_price") is not None
            and item.get("price_change_percentage_24h") is not None
            and float(item["price_change_percentage_24h"]) > 0
        ]
        quotes.sort(key=lambda item: item.change_24h, reverse=True)
    except Exception:
        logger.exception("Public crypto ticker request failed")
        with _cache_lock:
            return _crypto_cache[1][:limit]

    with _cache_lock:
        _crypto_cache = (now, quotes)
    return quotes[:limit]


def get_live_market_signals(limit: int = 12) -> list[dict[str, Any]]:
    """Read latest public XAUUSD signals directly from market_signals.

    This intentionally does not use an in-process cache, so the public
    `/signals` route reflects the latest trading table rows after refresh.
    """
    try:
        with session_scope() as session:
            columns = _table_columns(session, "market_signals")
            target_1 = (
                "target_1"
                if columns.get("target_1")
                else "target_price"
            )
            target_2 = (
                "target_2"
                if columns.get("target_2")
                else "NULL::numeric"
            )
            target_3 = (
                "target_3"
                if columns.get("target_3")
                else "NULL::numeric"
            )
            risk_level = (
                "risk_level"
                if columns.get("risk_level")
                else "NULL::text"
            )
            timeframe = (
                "timeframe"
                if columns.get("timeframe")
                else "NULL::text"
            )
            note = "note" if columns.get("note") else "NULL::text"
            rows = (
                session.execute(
                    text(
                        f"""
                        SELECT id, symbol, price, signal_type,
                               target_price, {target_1} AS target_1,
                               {target_2} AS target_2,
                               {target_3} AS target_3,
                               stop_loss, source, sheet_label,
                               {risk_level} AS risk_level,
                               {timeframe} AS timeframe,
                               {note} AS note,
                               signal_time, updated_at
                        FROM public.market_signals
                        WHERE signal_type IN ('BUY', 'SELL', 'HOLD')
                        ORDER BY signal_time DESC
                        LIMIT :limit
                        """
                    ),
                    {"limit": max(1, min(int(limit), 50))},
                )
                .mappings()
                .all()
            )
    except Exception:
        logger.exception("Live market signal loading failed")
        return []
    return [dict(row) for row in rows]


def _table_columns(session: Any, table_name: str) -> dict[str, bool]:
    rows = session.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = :table_name
            """
        ),
        {"table_name": table_name},
    ).scalars()
    return {str(column): True for column in rows}
