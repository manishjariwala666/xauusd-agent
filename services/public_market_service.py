"""Cached public XAUUSD and cryptocurrency market snapshot service."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
import time
from typing import Any

from loguru import logger
import requests

from services.market_data import MarketDataService


@dataclass(frozen=True)
class CryptoQuote:
    symbol: str
    name: str
    price_usd: float
    change_24h: float


_cache_lock = Lock()
_crypto_cache: tuple[float, list[CryptoQuote]] = (0.0, [])


def get_xauusd_snapshot(supabase: Any) -> dict[str, Any] | None:
    """Return a public-safe XAUUSD snapshot from the existing price service."""
    price = MarketDataService(supabase).fetch_current_price()
    if price is None:
        return None
    return {
        "symbol": price.symbol,
        "price": float(price.price),
        "observed_at": price.observed_at,
        "source": price.source,
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
            timeout=12,
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
