"""Read-only runtime wiring for VenusRealm Captain AI."""

from __future__ import annotations

import os

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from services.ai_agents.economic_calendar.engine import EconomicCalendarAI
from services.ai_agents.economic_calendar.provider import load_high_impact_events
from services.captain_ai_engine import CaptainAssessment, assess_captain
from services.marketaux_news_provider import load_marketaux_xauusd_context
from services.marketaux_macro_bias import assess_marketaux_macro_bias
from services.google_sheets import GoogleSheetsService
from services.master_ai_signal_reader import parse_signal_snapshot


INDIA_TIMEZONE = ZoneInfo("Asia/Kolkata")


def _trading_date(now: datetime) -> datetime.date:
    current = now.astimezone(INDIA_TIMEZONE)
    if (current.hour, current.minute) < (3, 30):
        current = current - timedelta(days=1)
    return current.date()


def run_captain_read_only(
    *,
    now: datetime | None = None,
) -> CaptainAssessment:
    current_time = now or datetime.now(INDIA_TIMEZONE)

    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=INDIA_TIMEZONE)
    else:
        current_time = current_time.astimezone(INDIA_TIMEZONE)

    target_date = _trading_date(current_time)

    sheets = GoogleSheetsService()
    values = sheets._analysis_values()

    current = parse_signal_snapshot(
        values,
        target_date=target_date,
    )

    if current is None:
        raise RuntimeError(
            f"Current Sheet snapshot not found for {target_date.isoformat()}."
        )

    history = []

    candidate = target_date - timedelta(days=1)

    # Scan backwards far enough to collect previous five actual Sheet dates,
    # skipping weekends/holidays/missing blocks safely.
    for _ in range(14):
        if len(history) >= 5:
            break

        snapshot = parse_signal_snapshot(
            values,
            target_date=candidate,
        )

        if snapshot is not None:
            history.append(snapshot)

        candidate -= timedelta(days=1)

    history.reverse()

    news_api_key = os.getenv(
        "TRADING_ECONOMICS_API_KEY",
        "",
    ).strip()

    if not news_api_key:
        from services.ai_agents.economic_calendar.models import (
            NewsLockDecision,
        )

        news_lock = NewsLockDecision(
            locked=True,
            reason=(
                "Economic calendar unavailable; "
                "Captain fails closed."
            ),
            event_id=None,
            seconds_to_event=None,
        )
    else:
        events = load_high_impact_events(
            now=current_time,
            hours_before=2,
            hours_after=24,
        )

        calendar = EconomicCalendarAI()

        # Captain uses a stricter XAUUSD safety window than the
        # shared economic-calendar defaults.
        news_lock = calendar.should_lock_signals(
            events,
            now=current_time,
            pre_lock_minutes=30,
            post_lock_minutes=30,
        )

    macro_context = load_marketaux_xauusd_context(
        now=current_time,
    )

    macro = assess_marketaux_macro_bias(
        macro_context,
    )

    return assess_captain(
        current=current,
        history=tuple(history),
        news_lock=news_lock,
        macro_bias=macro.bias.value,
        macro_confidence=macro.confidence,
    )
