from datetime import datetime, timedelta, timezone
from decimal import Decimal

from services.ai_agents.economic_calendar.engine import EconomicCalendarAI
from services.ai_agents.economic_calendar.models import (
    EconomicEvent,
    EventBias,
    EventCountry,
    EventImpact,
)


def test_high_impact_event_locks_signal_window() -> None:
    now = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)

    event = EconomicEvent(
        event_id="us-nfp-2026-08",
        country=EventCountry.USA,
        currency="USD",
        title="Non-Farm Employment Change",
        impact=EventImpact.HIGH,
        scheduled_at=now + timedelta(minutes=8),
    )

    decision = EconomicCalendarAI().should_lock_signals(
        (event,),
        now=now,
    )

    assert decision.locked is True
    assert decision.event_id == event.event_id


def test_strong_us_nfp_is_bearish_for_gold() -> None:
    event = EconomicEvent(
        event_id="us-nfp-2026-08",
        country=EventCountry.USA,
        currency="USD",
        title="Non-Farm Employment Change",
        impact=EventImpact.HIGH,
        scheduled_at=datetime(2026, 8, 7, tzinfo=timezone.utc),
        forecast=Decimal("150"),
        actual=Decimal("220"),
    )

    result = EconomicCalendarAI().assess_event(event)

    assert result.bias is EventBias.BEARISH_GOLD
    assert result.surprise == Decimal("70")


def test_higher_us_unemployment_is_bullish_for_gold() -> None:
    event = EconomicEvent(
        event_id="us-unemployment-2026-08",
        country=EventCountry.USA,
        currency="USD",
        title="Unemployment Rate",
        impact=EventImpact.HIGH,
        scheduled_at=datetime(2026, 8, 7, tzinfo=timezone.utc),
        forecast=Decimal("4.2"),
        actual=Decimal("4.4"),
    )

    result = EconomicCalendarAI().assess_event(event)

    assert result.bias is EventBias.BULLISH_GOLD


def test_medium_impact_event_does_not_lock_signals() -> None:
    now = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)

    event = EconomicEvent(
        event_id="us-medium-event",
        country=EventCountry.USA,
        currency="USD",
        title="Initial Jobless Claims",
        impact=EventImpact.MEDIUM,
        scheduled_at=now + timedelta(minutes=5),
    )

    decision = EconomicCalendarAI().should_lock_signals(
        (event,),
        now=now,
    )

    assert decision.locked is False


def test_canada_event_uses_canada_rule() -> None:
    event = EconomicEvent(
        event_id="ca-employment-2026-08",
        country=EventCountry.CANADA,
        currency="CAD",
        title="Employment Change",
        impact=EventImpact.HIGH,
        scheduled_at=datetime(2026, 8, 7, tzinfo=timezone.utc),
        forecast=Decimal("10"),
        actual=Decimal("30"),
    )

    result = EconomicCalendarAI().assess_event(event)

    assert result.bias is EventBias.BEARISH_GOLD
    assert result.surprise == Decimal("20")
