"""Typed contracts for economic calendar intelligence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from decimal import Decimal


class EventCountry(StrEnum):
    USA = "USA"
    CANADA = "CANADA"


class EventImpact(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class EventBias(StrEnum):
    BULLISH_GOLD = "BULLISH_GOLD"
    BEARISH_GOLD = "BEARISH_GOLD"
    NEUTRAL = "NEUTRAL"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class EconomicEvent:
    event_id: str
    country: EventCountry
    currency: str
    title: str
    impact: EventImpact
    scheduled_at: datetime
    previous: Decimal | None = None
    forecast: Decimal | None = None
    actual: Decimal | None = None
    source: str = "UNSPECIFIED"


@dataclass(frozen=True)
class NewsLockDecision:
    locked: bool
    reason: str
    event_id: str | None
    seconds_to_event: int | None


@dataclass(frozen=True)
class EventAssessment:
    event_id: str
    bias: EventBias
    surprise: Decimal | None
    confidence: int
    rationale: tuple[str, ...]
