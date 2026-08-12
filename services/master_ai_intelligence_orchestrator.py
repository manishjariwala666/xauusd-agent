"""Read-only intelligence synthesis for Venus Master AI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from services.ai_agents.economic_calendar.models import (
    EventAssessment,
    EventBias,
    NewsLockDecision,
)
from services.ai_agents.macro_ai.models import (
    GoldBias,
    MacroAssessment,
)


class IntelligenceDecision(StrEnum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    WAIT = "WAIT"
    INCOMPLETE = "INCOMPLETE"


@dataclass(frozen=True)
class MarketReference:
    price: str | None
    observed_at: datetime | None
    source: str
    fresh: bool
    label: str


@dataclass(frozen=True)
class UnifiedIntelligenceAssessment:
    decision: IntelligenceDecision
    confidence: int
    market: MarketReference
    macro_bias: str
    macro_confidence: int
    economic_bias: str
    economic_confidence: int
    news_locked: bool
    rationale: tuple[str, ...]
    conflicts: tuple[str, ...]
    read_only: bool = True
    signal_generated: bool = False
    execution_started: bool = False


def _economic_summary(
    assessments: tuple[EventAssessment, ...],
) -> tuple[str, int, tuple[str, ...]]:
    usable = [
        item
        for item in assessments
        if item.bias is not EventBias.UNKNOWN
    ]

    if not usable:
        return "UNKNOWN", 0, ()

    bullish = [
        item
        for item in usable
        if item.bias is EventBias.BULLISH_GOLD
    ]
    bearish = [
        item
        for item in usable
        if item.bias is EventBias.BEARISH_GOLD
    ]

    if len(bullish) > len(bearish):
        bias = "BULLISH_GOLD"
        selected = bullish
    elif len(bearish) > len(bullish):
        bias = "BEARISH_GOLD"
        selected = bearish
    else:
        bias = "NEUTRAL"
        selected = usable

    confidence = int(
        sum(item.confidence for item in selected)
        / max(1, len(selected))
    )

    rationale = tuple(
        f"{item.event_id}: {item.bias.value} ({item.confidence}%)"
        for item in usable
    )

    return bias, confidence, rationale


def synthesize_intelligence(
    *,
    market: MarketReference,
    macro: MacroAssessment | None,
    economic_assessments: tuple[EventAssessment, ...] = (),
    news_lock: NewsLockDecision | None = None,
) -> UnifiedIntelligenceAssessment:
    """Combine read-only intelligence without creating a signal."""

    rationale: list[str] = []
    conflicts: list[str] = []

    if news_lock is not None and news_lock.locked:
        rationale.append(
            f"News lock active: {news_lock.reason}"
        )

    macro_bias = macro.bias.value if macro else "UNKNOWN"
    macro_confidence = macro.confidence if macro else 0

    if macro is None:
        conflicts.append("Macro assessment unavailable.")
    else:
        rationale.append(
            f"Macro bias: {macro.bias.value} "
            f"({macro.confidence}%)"
        )
        conflicts.extend(macro.conflicts)

    economic_bias, economic_confidence, economic_rationale = (
        _economic_summary(economic_assessments)
    )
    rationale.extend(economic_rationale)

    if not market.fresh:
        conflicts.append(
            "Market reference is stale and cannot be treated as live."
        )

    if news_lock is not None and news_lock.locked:
        decision = IntelligenceDecision.WAIT
        confidence = max(
            macro_confidence,
            economic_confidence,
        )
    elif macro is None and economic_bias == "UNKNOWN":
        decision = IntelligenceDecision.INCOMPLETE
        confidence = 0
    else:
        bullish_score = 0
        bearish_score = 0

        if macro_bias == GoldBias.BUY.value:
            bullish_score += macro_confidence
        elif macro_bias == GoldBias.SELL.value:
            bearish_score += macro_confidence

        if economic_bias == "BULLISH_GOLD":
            bullish_score += economic_confidence
        elif economic_bias == "BEARISH_GOLD":
            bearish_score += economic_confidence

        if bullish_score > bearish_score:
            decision = IntelligenceDecision.BULLISH
            confidence = min(
                95,
                int(bullish_score / max(1, len(
                    [
                        value
                        for value in (
                            macro_confidence
                            if macro_bias == GoldBias.BUY.value
                            else 0,
                            economic_confidence
                            if economic_bias == "BULLISH_GOLD"
                            else 0,
                        )
                        if value
                    ]
                ))),
            )
        elif bearish_score > bullish_score:
            decision = IntelligenceDecision.BEARISH
            confidence = min(
                95,
                int(bearish_score / max(1, len(
                    [
                        value
                        for value in (
                            macro_confidence
                            if macro_bias == GoldBias.SELL.value
                            else 0,
                            economic_confidence
                            if economic_bias == "BEARISH_GOLD"
                            else 0,
                        )
                        if value
                    ]
                ))),
            )
        else:
            decision = IntelligenceDecision.NEUTRAL
            confidence = max(
                macro_confidence,
                economic_confidence,
            )

    if not market.fresh and decision in {
        IntelligenceDecision.BULLISH,
        IntelligenceDecision.BEARISH,
    }:
        rationale.append(
            "Directional view is reference-only because market data is stale."
        )

    return UnifiedIntelligenceAssessment(
        decision=decision,
        confidence=confidence,
        market=market,
        macro_bias=macro_bias,
        macro_confidence=macro_confidence,
        economic_bias=economic_bias,
        economic_confidence=economic_confidence,
        news_locked=bool(news_lock and news_lock.locked),
        rationale=tuple(rationale),
        conflicts=tuple(dict.fromkeys(conflicts)),
    )


def format_intelligence_response(
    assessment: UnifiedIntelligenceAssessment,
) -> str:
    """Return a safe admin-readable intelligence summary."""

    lines = [
        "VenusRealm Read-Only Intelligence",
        f"Decision: {assessment.decision.value}",
        f"Confidence: {assessment.confidence}%",
        f"Market: {assessment.market.label}",
        f"Market Price: {assessment.market.price or 'Unavailable'}",
        f"Macro: {assessment.macro_bias} "
        f"({assessment.macro_confidence}%)",
        f"Economic: {assessment.economic_bias} "
        f"({assessment.economic_confidence}%)",
        f"News Lock: {'ACTIVE' if assessment.news_locked else 'INACTIVE'}",
    ]

    if assessment.rationale:
        lines.append("Rationale:")
        lines.extend(f"- {item}" for item in assessment.rationale)

    if assessment.conflicts:
        lines.append("Conflicts:")
        lines.extend(f"- {item}" for item in assessment.conflicts)

    lines.extend(
        [
            "Read-only assessment only.",
            "No signal, trade, Telegram, WhatsApp or publication was generated.",
        ]
    )

    return "\n".join(lines)
