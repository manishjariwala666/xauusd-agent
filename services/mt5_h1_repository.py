"""Storage boundaries for MT5 XAUUSD H1 candles.

This module does not create tables or run migrations.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from threading import Lock
from typing import Protocol


@dataclass(frozen=True)
class H1Candle:
    symbol: str
    broker_symbol: str
    broker_server: str
    candle_start_utc: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    source_event_id: str
    received_at_utc: datetime
    source: str = "MT5"


class H1Repository(Protocol):
    def event_exists(self, source_event_id: str) -> bool:
        ...

    def save_candle(self, candle: H1Candle) -> H1Candle:
        ...

    def latest_candle(self, symbol: str) -> H1Candle | None:
        ...


class InMemoryH1Repository:
    """Thread-safe repository used for local development and tests."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._events: set[str] = set()
        self._candles: dict[tuple[str, datetime], H1Candle] = {}

    def event_exists(self, source_event_id: str) -> bool:
        with self._lock:
            return source_event_id in self._events

    def save_candle(self, candle: H1Candle) -> H1Candle:
        key = (candle.symbol, candle.candle_start_utc)

        with self._lock:
            existing = self._candles.get(key)

            if existing and candle.received_at_utc < existing.received_at_utc:
                return existing

            self._candles[key] = candle
            self._events.add(candle.source_event_id)
            return candle

    def latest_candle(self, symbol: str) -> H1Candle | None:
        normalized = symbol.strip().upper()

        with self._lock:
            matching = [
                candle
                for candle in self._candles.values()
                if candle.symbol == normalized
            ]

        if not matching:
            return None

        return max(
            matching,
            key=lambda candle: (
                candle.candle_start_utc,
                candle.received_at_utc,
            ),
        )
