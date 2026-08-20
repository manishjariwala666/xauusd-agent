"""Read-only runtime wiring for VenusRealm Captain AI."""

from __future__ import annotations

import os

from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
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
    buy_targets: tuple[Decimal, ...]
    sell_targets: tuple[Decimal, ...]


def _trading_date(now: datetime) -> date:
    current = now.astimezone(INDIA_TIMEZONE)
    if (current.hour, current.minute) < (3, 30):
        current = current - timedelta(days=1)
    return current.date()


def _load_current_history_values(
    current_time: datetime,
) -> tuple[
    MasterAISignalSnapshot,
    tuple[MasterAISignalSnapshot, ...],
    list[list[object]],
]:
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
    return current, tuple(history), values


def _load_current_and_history(
    current_time: datetime,
) -> tuple[MasterAISignalSnapshot, tuple[MasterAISignalSnapshot, ...]]:
    current, history, _ = _load_current_history_values(current_time)
    return current, history


def _normalize_now(now: datetime | None) -> datetime:
    current_time = now or datetime.now(INDIA_TIMEZONE)
    if current_time.tzinfo is None:
        return current_time.replace(tzinfo=INDIA_TIMEZONE)
    return current_time.astimezone(INDIA_TIMEZONE)


def _decimal(value: object) -> Decimal | None:
    text = str(value or "").strip().replace(",", "")
    if not text:
        return None
    try:
        return Decimal(text)
    except Exception:
        return None


def _canonical_identity(external_key: object) -> tuple[str, str] | None:
    parts = str(external_key or "").strip().split(":")
    if len(parts) != 4 or parts[0] != "gsheet-session":
        return None
    session_date, session_name = parts[1], parts[2].lower()
    if session_name not in {"morning", "evening"}:
        return None
    try:
        date.fromisoformat(session_date)
    except ValueError:
        return None
    return session_date, session_name


def _snapshot_as_of(
    current: MasterAISignalSnapshot,
    values: list[list[object]],
    *,
    current_time: datetime,
    session_name: str | None = None,
) -> MasterAISignalSnapshot:
    """Rebuild active-session extrema and CMP from bars closed by ``current_time``."""
    from services.sheet_signal_source import (
        _session_context_from_values,
        _slot_bounds,
    )

    session_date = current.signal_date.isoformat()
    sheets = GoogleSheetsService()
    normalized_now = current_time.astimezone(timezone.utc)
    eligible: list[tuple[datetime, str, list[object]]] = []
    in_block = False

    for row in values:
        first = str(row[0] if row else "").strip()
        header = sheets._SESSION_HEADER.match(first)
        if header:
            in_block = header.group(1) == session_date
            continue
        if not in_block or len(row) < 6:
            continue
        bounds = _slot_bounds(sheets, first, session_date=session_date)
        if bounds is None:
            continue
        _, closed_at, row_session = bounds
        if normalized_now < closed_at:
            continue
        eligible.append((closed_at, row_session, row))

    if not eligible:
        return current

    if session_name is None:
        session_name = max(eligible, key=lambda item: item[0])[1]
    session_rows = [item for item in eligible if item[1] == session_name]
    if not session_rows:
        return current

    context = _session_context_from_values(
        sheets,
        values,
        session_date=session_date,
        session_name=session_name,
    )
    if context is None:
        return current

    _, _, buy_base, sell_base, buy_targets, sell_targets = context
    highs = [_decimal(item[2][1]) for item in session_rows]
    lows = [_decimal(item[2][2]) for item in session_rows]
    usable_highs = [value for value in highs if value is not None]
    usable_lows = [value for value in lows if value is not None]
    latest = max(session_rows, key=lambda item: item[0])
    latest_row = latest[2]
    latest_cmp = _decimal(latest_row[5])

    return replace(
        current,
        day_high=max(usable_highs) if usable_highs else current.day_high,
        day_low=min(usable_lows) if usable_lows else current.day_low,
        buy_base=buy_base,
        sell_base=sell_base,
        latest_slot=str(latest_row[0] or "").strip() or current.latest_slot,
        live_cmp=latest_cmp if latest_cmp is not None else current.live_cmp,
        buy_targets=buy_targets,
        sell_targets=sell_targets,
    )


def _news_and_macro(current_time: datetime) -> tuple[Any, Any]:
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
    return news_lock, macro


def _observed_result(
    current: MasterAISignalSnapshot,
    assessment: CaptainAssessment,
) -> CaptainObservedRun:
    return CaptainObservedRun(
        assessment=assessment,
        signal_date=current.signal_date,
        source=current.source,
        day_high=current.day_high,
        day_low=current.day_low,
        live_cmp=current.live_cmp,
        buy_base=current.buy_base,
        sell_base=current.sell_base,
        buy_targets=current.buy_targets,
        sell_targets=current.sell_targets,
    )


def run_captain_observed(
    *,
    now: datetime | None = None,
) -> CaptainObservedRun:
    """Run Captain once and retain the exact Sheet market context used."""
    current_time = _normalize_now(now)
    current, history, values = _load_current_history_values(current_time)
    current = _snapshot_as_of(
        current,
        values,
        current_time=current_time,
    )
    news_lock, macro = _news_and_macro(current_time)
    assessment = assess_captain(
        current=current,
        history=history,
        news_lock=news_lock,
        macro_bias=macro.bias.value,
        macro_confidence=macro.confidence,
    )
    return _observed_result(current, assessment)


def run_captain_sheet_candidate(
    signal: Any,
) -> CaptainObservedRun:
    """Evaluate one canonical Sheet candidate at its Base entry and trigger time.

    This keeps the configured Buy/Sell Base as entry instead of substituting a
    later CMP. Trigger-time closed bars are used for session extrema so a later
    opposite-base sweep cannot retrospectively invalidate an earlier one-sided
    base trigger.
    """
    external_key = (
        signal.get("external_key")
        if isinstance(signal, dict)
        else getattr(signal, "external_key", "")
    )
    identity = _canonical_identity(external_key)
    if identity is None:
        return run_captain_observed()
    _, session_name = identity

    def field(name: str, default: Any = None) -> Any:
        if isinstance(signal, dict):
            return signal.get(name, default)
        return getattr(signal, name, default)

    raw_time = field("signal_time") or field("observed_at")
    if isinstance(raw_time, datetime):
        observed_at = raw_time
    else:
        text = str(raw_time or "").strip()
        if not text:
            raise RuntimeError("Canonical Sheet candidate is missing trigger time.")
        observed_at = datetime.fromisoformat(text.replace("Z", "+00:00"))
    current_time = _normalize_now(observed_at)

    current, history, values = _load_current_history_values(current_time)
    current = _snapshot_as_of(
        current,
        values,
        current_time=current_time,
        session_name=session_name,
    )

    direction = str(field("signal_type") or field("direction") or "").strip().upper()
    entry = _decimal(field("price") if field("price") is not None else field("reference_price"))
    stop_loss = _decimal(field("stop_loss"))
    if direction not in {"BUY", "SELL"} or entry is None or stop_loss is None:
        raise RuntimeError("Canonical Sheet candidate direction, entry or stop is invalid.")

    raw_targets: list[Decimal] = []
    numbered = [field(f"target_{slot}") for slot in range(1, 7)]
    if any(value not in (None, "") for value in numbered):
        for value in numbered:
            parsed = _decimal(value)
            if parsed is not None:
                raw_targets.append(parsed)
    else:
        for value in tuple(field("targets", ()) or ())[:6]:
            parsed = _decimal(value)
            if parsed is not None:
                raw_targets.append(parsed)

    if len(raw_targets) != 6:
        raise RuntimeError("Canonical Sheet candidate must provide Target 1 through Target 6.")

    current = replace(
        current,
        live_cmp=entry,
        day_low=stop_loss if direction == "BUY" else current.day_low,
        day_high=stop_loss if direction == "SELL" else current.day_high,
        buy_targets=tuple(raw_targets) if direction == "BUY" else current.buy_targets,
        sell_targets=tuple(raw_targets) if direction == "SELL" else current.sell_targets,
    )
    news_lock, macro = _news_and_macro(current_time)
    assessment = assess_captain(
        current=current,
        history=history,
        news_lock=news_lock,
        macro_bias=macro.bias.value,
        macro_confidence=macro.confidence,
    )
    return _observed_result(current, assessment)


def run_captain_read_only(
    *,
    now: datetime | None = None,
) -> CaptainAssessment:
    """Run Captain, preferring the authoritative canonical Sheet candidate."""
    current_time = _normalize_now(now)
    try:
        from services.sheet_signal_source import load_authoritative_sheet_signal

        candidate = load_authoritative_sheet_signal(
            GoogleSheetsService(),
            now=current_time.astimezone(timezone.utc),
        )
        if candidate is not None and _canonical_identity(candidate.external_key):
            return run_captain_sheet_candidate(candidate).assessment
    except Exception:
        # Preserve fail-closed behavior in the ordinary observed Captain path.
        pass
    return run_captain_observed(now=current_time).assessment
