"""Deterministic macro-news bias for XAUUSD.

Secondary context only.
Never overrides the economic-calendar hard safety lock.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from services.marketaux_news_provider import MarketauxContext


class MacroGoldBias(StrEnum):
    BULLISH_GOLD = "BULLISH_GOLD"
    BEARISH_GOLD = "BEARISH_GOLD"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class MacroBiasAssessment:
    bias: MacroGoldBias
    bullish_score: int
    bearish_score: int
    confidence: int
    reasons: tuple[str, ...]


BULLISH_PHRASES = (
    "rate hike bets fade",
    "rate hike in doubt",
    "rate cut",
    "softer inflation",
    "mild inflation",
    "inflation falls",
    "dollar weakens",
    "dollar weakness",
    "downside in us dollar",
    "yields fall",
    "treasury yields fall",
    "unemployment claims rise",
)

BEARISH_PHRASES = (
    "rate hike",
    "hawkish",
    "inflation rises",
    "hot inflation",
    "strong inflation",
    "dollar strengthens",
    "dollar strength",
    "yields rise",
    "treasury yields rise",
    "payrolls beat",
    "jobs beat",
)


def assess_marketaux_macro_bias(
    context: MarketauxContext,
) -> MacroBiasAssessment:
    if not context.available:
        return MacroBiasAssessment(
            bias=MacroGoldBias.UNKNOWN,
            bullish_score=0,
            bearish_score=0,
            confidence=0,
            reasons=("Marketaux context unavailable.",),
        )

    bullish = 0
    bearish = 0
    reasons: list[str] = []

    for item in context.headlines:
        text = item.title.lower()
        weight = max(1, item.relevance_score)

        bullish_hit = any(
            phrase in text
            for phrase in BULLISH_PHRASES
        )

        bearish_hit = any(
            phrase in text
            for phrase in BEARISH_PHRASES
        )

        # Avoid double-counting generic "rate hike" when headline
        # explicitly says hike bets fade / hike in doubt.
        if bullish_hit:
            bullish += weight
            reasons.append(
                f"BULLISH +{weight}: {item.title}"
            )
            continue

        if bearish_hit:
            bearish += weight
            reasons.append(
                f"BEARISH +{weight}: {item.title}"
            )

    total = bullish + bearish

    if total == 0:
        return MacroBiasAssessment(
            bias=MacroGoldBias.UNKNOWN,
            bullish_score=0,
            bearish_score=0,
            confidence=0,
            reasons=("No deterministic macro-direction phrase matched.",),
        )

    difference = bullish - bearish

    if difference >= 5:
        bias = MacroGoldBias.BULLISH_GOLD
    elif difference <= -5:
        bias = MacroGoldBias.BEARISH_GOLD
    else:
        bias = MacroGoldBias.MIXED

    confidence = min(
        95,
        int(abs(difference) / total * 100)
        if total
        else 0,
    )

    return MacroBiasAssessment(
        bias=bias,
        bullish_score=bullish,
        bearish_score=bearish,
        confidence=confidence,
        reasons=tuple(reasons[:10]),
    )
