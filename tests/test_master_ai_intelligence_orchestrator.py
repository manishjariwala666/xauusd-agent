from datetime import datetime, timezone
from decimal import Decimal

from services.ai_agents.economic_calendar.models import (
    EventAssessment,
    EventBias,
    NewsLockDecision,
)
from services.ai_agents.macro_ai.models import (
    GoldBias,
    MacroAssessment,
)
from services.master_ai_intelligence_orchestrator import (
    IntelligenceDecision,
    MarketReference,
    format_intelligence_response,
    synthesize_intelligence,
)


def macro(
    bias: GoldBias,
    confidence: int,
) -> MacroAssessment:
    return MacroAssessment(
        bias=bias,
        confidence=confidence,
        total_score=Decimal("1"),
        observed_at=datetime.now(timezone.utc),
        drivers=(),
        conflicts=(),
        source_count=3,
    )


def market(*, fresh: bool = True) -> MarketReference:
    return MarketReference(
        price="4246.65",
        observed_at=datetime.now(timezone.utc),
        source="GOOGLE_SHEET",
        fresh=fresh,
        label=(
            "Verified current Sheet reference"
            if fresh
            else "Stale Sheet reference"
        ),
    )


def test_news_lock_forces_wait() -> None:
    result = synthesize_intelligence(
        market=market(),
        macro=macro(GoldBias.BUY, 80),
        news_lock=NewsLockDecision(
            locked=True,
            reason="USA high-impact event window",
            event_id="us-nfp",
            seconds_to_event=300,
        ),
    )

    assert result.decision is IntelligenceDecision.WAIT
    assert result.news_locked is True
    assert result.signal_generated is False


def test_aligned_macro_and_economic_bias_is_bullish() -> None:
    result = synthesize_intelligence(
        market=market(),
        macro=macro(GoldBias.BUY, 82),
        economic_assessments=(
            EventAssessment(
                event_id="us-cpi",
                bias=EventBias.BULLISH_GOLD,
                surprise=Decimal("-0.2"),
                confidence=75,
                rationale=("USD-negative surprise.",),
            ),
        ),
    )

    assert result.decision is IntelligenceDecision.BULLISH
    assert result.confidence > 0


def test_conflicting_bias_is_neutral() -> None:
    result = synthesize_intelligence(
        market=market(),
        macro=macro(GoldBias.BUY, 70),
        economic_assessments=(
            EventAssessment(
                event_id="us-nfp",
                bias=EventBias.BEARISH_GOLD,
                surprise=Decimal("40"),
                confidence=70,
                rationale=("USD-supportive surprise.",),
            ),
        ),
    )

    assert result.decision is IntelligenceDecision.NEUTRAL


def test_stale_market_is_explicitly_flagged() -> None:
    result = synthesize_intelligence(
        market=market(fresh=False),
        macro=macro(GoldBias.SELL, 75),
    )

    assert any(
        "stale" in conflict.lower()
        for conflict in result.conflicts
    )

    output = format_intelligence_response(result)

    assert "Read-only assessment only." in output
    assert "No signal" in output
