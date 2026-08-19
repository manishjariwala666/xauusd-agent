"""Typed contracts for the read-only Venus Macro AI engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class MarketDirection(StrEnum):
    UP = "UP"
    DOWN = "DOWN"
    FLAT = "FLAT"


class GoldBias(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    NEUTRAL = "NEUTRAL"


@dataclass(frozen=True)
class MarketSnapshot:
    symbol: str
    price: Decimal
    change_percent: Decimal
    direction: MarketDirection
    observed_at: datetime
    source: str


@dataclass(frozen=True)
class MacroDriverScore:
    symbol: str
    weight: Decimal
    normalized_score: Decimal
    contribution: Decimal
    rationale: str


@dataclass(frozen=True)
class MacroAssessment:
    bias: GoldBias
    confidence: int
    total_score: Decimal
    observed_at: datetime
    drivers: tuple[MacroDriverScore, ...]
    conflicts: tuple[str, ...]
    source_count: int
