from datetime import datetime, timezone
from decimal import Decimal

from services.ai_agents.macro_ai.engine import VenusMacroAI
from services.ai_agents.macro_ai.models import (
    GoldBias,
    MarketDirection,
    MarketSnapshot,
)


def snapshot(
    symbol: str,
    direction: MarketDirection,
) -> MarketSnapshot:
    return MarketSnapshot(
        symbol=symbol,
        price=Decimal("100"),
        change_percent=Decimal("1"),
        direction=direction,
        observed_at=datetime(2026, 8, 6, tzinfo=timezone.utc),
        source="TEST",
    )


def test_macro_ai_returns_buy_when_gold_supportive_drivers_dominate() -> None:
    result = VenusMacroAI().assess(
        (
            snapshot("DXY", MarketDirection.DOWN),
            snapshot("US10Y", MarketDirection.DOWN),
            snapshot("US2Y", MarketDirection.DOWN),
            snapshot("VIX", MarketDirection.UP),
            snapshot("XAGUSD", MarketDirection.UP),
            snapshot("SPX500", MarketDirection.DOWN),
            snapshot("US30", MarketDirection.DOWN),
            snapshot("NASDAQ100", MarketDirection.DOWN),
            snapshot("USOIL", MarketDirection.UP),
            snapshot("BTCUSD", MarketDirection.DOWN),
        )
    )

    assert result.bias is GoldBias.BUY
    assert result.total_score > Decimal("0")
    assert result.source_count == 10
    assert result.conflicts == ()


def test_macro_ai_reports_missing_sources_without_guessing() -> None:
    result = VenusMacroAI().assess(
        (
            snapshot("DXY", MarketDirection.FLAT),
        )
    )

    assert result.bias is GoldBias.NEUTRAL
    assert result.source_count == 1
    assert len(result.conflicts) == 9
