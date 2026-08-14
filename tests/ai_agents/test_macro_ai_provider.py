from datetime import datetime, timezone
from decimal import Decimal

import pandas as pd

from services.ai_agents.macro_ai.models import MarketDirection
from services.ai_agents.macro_ai.provider import (
    _snapshot,
    load_macro_assessment,
)


class FakeTicker:
    def __init__(self, symbol: str) -> None:
        self.symbol = symbol

    def history(self, **_: object) -> pd.DataFrame:
        return pd.DataFrame(
            {"Close": [100.0, 102.0]},
            index=pd.DatetimeIndex(
                [
                    datetime(2026, 8, 5, tzinfo=timezone.utc),
                    datetime(2026, 8, 6, tzinfo=timezone.utc),
                ]
            ),
        )


def test_provider_normalizes_yahoo_snapshot(monkeypatch) -> None:
    monkeypatch.setattr(
        "services.ai_agents.macro_ai.provider.yf.Ticker",
        FakeTicker,
    )

    snapshot = _snapshot("DXY", "DX-Y.NYB")

    assert snapshot is not None
    assert snapshot.price == Decimal("102.0")
    assert snapshot.change_percent == Decimal("2.0000")
    assert snapshot.direction is MarketDirection.UP
    assert snapshot.source == "YAHOO_FINANCE:DX-Y.NYB"


def test_provider_builds_read_only_macro_assessment(monkeypatch) -> None:
    monkeypatch.setattr(
        "services.ai_agents.macro_ai.provider.yf.Ticker",
        FakeTicker,
    )

    result = load_macro_assessment()

    assert result is not None
    assert result.source_count > 0
    assert result.conflicts
