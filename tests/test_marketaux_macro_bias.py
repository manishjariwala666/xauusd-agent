from services.marketaux_macro_bias import (
    MacroGoldBias,
    assess_marketaux_macro_bias,
)
from services.marketaux_news_provider import (
    MacroHeadline,
    MarketauxContext,
)


def context_with(*titles: str) -> MarketauxContext:
    headlines = tuple(
        MacroHeadline(
            title=title,
            source="test",
            published_at="2026-08-14T00:00:00Z",
            url="https://example.com",
            relevance_score=5,
            themes=("FED", "INFLATION"),
        )
        for title in titles
    )

    return MarketauxContext(
        available=True,
        headlines=headlines,
        reason="test",
    )


def test_bullish_gold_macro_bias():
    result = assess_marketaux_macro_bias(
        context_with(
            "Gold advances as mild inflation puts Fed rate hike in doubt",
            "Dollar weakness supports gold",
        )
    )

    assert result.bias is MacroGoldBias.BULLISH_GOLD
    assert result.bullish_score > result.bearish_score


def test_bearish_gold_macro_bias():
    result = assess_marketaux_macro_bias(
        context_with(
            "Hot inflation revives Fed rate hike expectations",
            "Treasury yields rise as dollar strengthens",
        )
    )

    assert result.bias is MacroGoldBias.BEARISH_GOLD
    assert result.bearish_score > result.bullish_score


def test_mixed_macro_bias():
    result = assess_marketaux_macro_bias(
        context_with(
            "Rate cut hopes support gold",
            "Dollar strengthens as yields rise",
        )
    )

    assert result.bias is MacroGoldBias.MIXED


def test_unavailable_context_is_unknown():
    result = assess_marketaux_macro_bias(
        MarketauxContext(
            available=False,
            headlines=(),
            reason="missing",
        )
    )

    assert result.bias is MacroGoldBias.UNKNOWN
