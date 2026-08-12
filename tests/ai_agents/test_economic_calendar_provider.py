from datetime import datetime, timezone
from decimal import Decimal

from services.ai_agents.economic_calendar.models import EventCountry
from services.ai_agents.economic_calendar.provider import (
    load_high_impact_events,
    parse_calendar_event,
)


def test_provider_parses_high_impact_us_event() -> None:
    event = parse_calendar_event(
        {
            "CalendarId": "123",
            "Date": "2026-08-07T12:30:00",
            "Country": "United States",
            "Event": "Non Farm Payrolls",
            "Importance": 3,
            "Actual": "220K",
            "Previous": "180K",
            "Forecast": "170K",
            "Source": "U.S. Bureau of Labor Statistics",
        }
    )

    assert event is not None
    assert event.country is EventCountry.USA
    assert event.actual == Decimal("220000")
    assert event.forecast == Decimal("170000")
    assert event.scheduled_at.tzinfo is not None


def test_provider_rejects_non_high_impact_event() -> None:
    assert parse_calendar_event(
        {
            "CalendarId": "124",
            "Date": "2026-08-07T12:30:00",
            "Country": "Canada",
            "Event": "Minor Event",
            "Importance": 2,
        }
    ) is None


def test_missing_api_key_returns_empty_events(monkeypatch) -> None:
    monkeypatch.delenv("TRADING_ECONOMICS_API_KEY", raising=False)

    events = load_high_impact_events(
        now=datetime(2026, 8, 7, tzinfo=timezone.utc),
    )

    assert events == ()
