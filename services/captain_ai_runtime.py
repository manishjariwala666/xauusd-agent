"""Read-only runtime wiring for VenusRealm Captain AI."""

from __future__ import annotations

import os

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from services.ai_agents.economic_calendar.engine import EconomicCalendarAI
from services.ai_agents.economic_calendar.provider import load_high_impact_events
from services.captain_ai_engine import CaptainAssessment, assess_captain
from services.marketaux_news_provider import load_marketaux_xauusd_context
from services.marketaux_macro_bias import assess_marketaux_macro_bias
from services.google_sheets import GoogleSheetsService
from services.master_ai_signal_reader import MasterAISignalSnapshot, parse_signal_snapshot


INDIA_TIMEZONE = ZoneInfo("Asia/Kolkata")


@dataclass(frozen=True)
class CaptainObservedRun:
    assessment: CaptainAssessment
    signal_date: date
    source: str
    day_high: Decimal | None
    day_low: Decimal | None
    live_cmp: Decimal | None
    buy_base: Decimal | None
    sell_base: Decimal | None


def _trading_date(now: datetime) -> date:
    current = now.astimezone(INDIA_TIMEZONE)
    if (current.hour, current.minute) < (3, 30):
        current = current - timedelta(days=1)
    return current.date()


def _load_current_and_history(
    current_time: datetime,
) -> tuple[MasterAISignalSnapshot, tuple[MasterAISignalSnapshot, ...]]:
    target_date = _trading_date(current_time)
    values = GoogleSheetsService()._analysis_values()
    current = parse_signal_snapshot(values, target_date=target_date)

    if current is None:
        raise RuntimeError(
            f"Current Sheet snapshot not found for {target_date.isoformat()}."
        )

    history: list[MasterAISignalSnapshot] = []
    candidate = target_date - timedelta(days=1)
    for _ in range(14):
        if len(history) >= 5:
            break
        snapshot = parse_signal_snapshot(values, target_date=candidate)
        if snapshot is not None:
            history.append(snapshot)
        candidate -= timedelta(days=1)
    history.reverse()
    return current, tuple(history)


def _normalize_now(now: datetime | None) -> datetime:
    current_time = now or datetime.now(INDIA_TIMEZONE)
    if current_time.tzinfo is None:
        return current_time.replace(tzinfo=INDIA_TIMEZONE)
    return current_time.astimezone(INDIA_TIMEZONE)


def run_captain_observed(
    *,
    now: datetime | None = None,
) -> CaptainObservedRun:
    """Run Captain once and retain the exact Sheet market context used."""
    current_time = _normalize_now(now)
    current, history = _load_current_and_history(current_time)

    news_api_key = os.getenv("TRADING_ECONOMICS_API_KEY", "").strip()
    if not news_api_key:
        from services.ai_agents.economic_calendar.models import NewsLockDecision

        news_lock = NewsLockDecision(
            locked=True,
            reason="Economic calendar unavailable; Captain fails closed.",
            event_id=None,
            seconds_to_event=None,
        )
    else:
        events = load_high_impact_events(
            now=current_time,
            hours_before=2,
            hours_after=24,
        )
        news_lock = EconomicCalendarAI().should_lock_signals(
            events,
            now=current_time,
            pre_lock_minutes=30,
            post_lock_minutes=30,
        )

    macro = assess_marketaux_macro_bias(
        load_marketaux_xauusd_context(now=current_time)
    )
    assessment = assess_captain(
        current=current,
        history=history,
        news_lock=news_lock,
        macro_bias=macro.bias.value,
        macro_confidence=macro.confidence,
    )
    return CaptainObservedRun(
        assessment=assessment,
        signal_date=current.signal_date,
        source=current.source,
        day_high=current.day_high,
        day_low=current.day_low,
        live_cmp=current.live_cmp,
        buy_base=current.buy_base,
        sell_base=current.sell_base,
    )


def run_captain_read_only(
    *,
    now: datetime | None = None,
) -> CaptainAssessment:
    """Backward-compatible Captain assessment entry point."""
    return run_captain_observed(now=now).assessment
