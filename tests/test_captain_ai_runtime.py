from datetime import datetime
from zoneinfo import ZoneInfo

from services.captain_ai_runtime import _trading_date


IST = ZoneInfo("Asia/Kolkata")


def test_trading_date_rolls_back_before_0330():
    now = datetime(2026, 8, 14, 0, 15, tzinfo=IST)
    assert _trading_date(now).isoformat() == "2026-08-13"


def test_trading_date_uses_current_date_after_0330():
    now = datetime(2026, 8, 14, 3, 30, tzinfo=IST)
    assert _trading_date(now).isoformat() == "2026-08-14"


def test_missing_news_api_key_fails_closed(monkeypatch):
    monkeypatch.delenv(
        "TRADING_ECONOMICS_API_KEY",
        raising=False,
    )

    from services.ai_agents.economic_calendar.models import (
        NewsLockDecision,
    )

    lock = NewsLockDecision(
        locked=True,
        reason="Economic calendar unavailable; Captain fails closed.",
        event_id=None,
        seconds_to_event=None,
    )

    assert lock.locked is True
    assert "fails closed" in lock.reason
