"""Approved USA and Canada economic events."""

from __future__ import annotations

from dataclasses import dataclass

from .models import EventCountry, EventImpact


@dataclass(frozen=True)
class EventRule:
    key: str
    country: EventCountry
    impact: EventImpact
    stronger_actual_supports_usd: bool


EVENT_RULES: tuple[EventRule, ...] = (
    EventRule("non-farm employment change", EventCountry.USA, EventImpact.HIGH, True),
    EventRule("unemployment rate", EventCountry.USA, EventImpact.HIGH, False),
    EventRule("average hourly earnings", EventCountry.USA, EventImpact.HIGH, True),
    EventRule("consumer price index", EventCountry.USA, EventImpact.HIGH, True),
    EventRule("core consumer price index", EventCountry.USA, EventImpact.HIGH, True),
    EventRule("core pce price index", EventCountry.USA, EventImpact.HIGH, True),
    EventRule("federal funds rate", EventCountry.USA, EventImpact.HIGH, True),
    EventRule("fomc statement", EventCountry.USA, EventImpact.HIGH, True),
    EventRule("retail sales", EventCountry.USA, EventImpact.HIGH, True),
    EventRule("ism manufacturing pmi", EventCountry.USA, EventImpact.HIGH, True),
    EventRule("ism services pmi", EventCountry.USA, EventImpact.HIGH, True),
    EventRule("initial jobless claims", EventCountry.USA, EventImpact.MEDIUM, False),
    EventRule("employment change", EventCountry.CANADA, EventImpact.HIGH, True),
    EventRule("unemployment rate", EventCountry.CANADA, EventImpact.HIGH, False),
    EventRule("bank of canada rate", EventCountry.CANADA, EventImpact.HIGH, True),
    EventRule("canada consumer price index", EventCountry.CANADA, EventImpact.HIGH, True),
)
