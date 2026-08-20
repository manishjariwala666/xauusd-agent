"""Authoritative Google Sheet source selection for outbound signals.

The canonical analysis worksheet owns delivery whenever DATE:/XAUUSD SESSION
blocks are present. This prevents an older structured BUY/SELL row from
silently overriding repaired session entry/SL/TP values used by Telegram and
WhatsApp.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from loguru import logger

from services.google_sheets import GoogleSheetsService, SheetSignal
from services.master_ai_signal_reader import parse_signal_snapshot
from services.sheet_reversal_guard import latest_two_bar_break, session_for_slot


_INDIA = ZoneInfo("Asia/Kolkata")


def _decimal(value: object) -> Decimal | None:
    text = str(value or "").strip().replace(",", "")
    if not text:
        return None
    try:
        return Decimal(text)
    except Exception:
        return None


def _slot_bounds(
    sheets: GoogleSheetsService,
    label: str,
    *,
    session_date: str,
) -> tuple[datetime, datetime, str] | None:
    slot_pattern = getattr(sheets, "_SLOT_LABEL", GoogleSheetsService._SLOT_LABEL)
    match = slot_pattern.match(label.strip())
    if not match:
        return None

    def resolve(hour_text: str, minute_text: str, meridiem: str) -> tuple[int, int]:
        hour = int(hour_text)
        minute = int(minute_text)
        meridiem = meridiem.upper()
        if meridiem:
            hour %= 12
            if meridiem == "PM":
                hour += 12
        return hour, minute

    start_hour, start_minute = resolve(
        match.group(1), match.group(2), str(match.group(3) or "")
    )
    end_hour, end_minute = resolve(
        match.group(4), match.group(5), str(match.group(6) or "")
    )
    started = datetime.strptime(
        f"{session_date} {start_hour:02d}:{start_minute:02d}",
        "%Y-%m-%d %H:%M",
    ).replace(tzinfo=_INDIA)
    closed = started.replace(hour=end_hour, minute=end_minute)
    if closed <= started:
        closed += timedelta(days=1)

    local_minutes = start_hour * 60 + start_minute
    if 210 <= local_minutes < 870:
        session_name = "morning"
    elif local_minutes >= 870 or local_minutes <= 150:
        session_name = "evening"
    else:
        return None
    return started.astimezone(timezone.utc), closed.astimezone(timezone.utc), session_name


def _base_cross_signal(
    sheets: GoogleSheetsService,
    values: list[list[object]],
    *,
    now: datetime,
) -> SheetSignal | None:
    """Return the first closed one-sided Buy/Sell Base cross for the live session.

    Buy Base and Sell Base are the configured trigger/entry levels. A base cross
    is actionable only after that bar closes on the directional side of the
    base. This prevents intrabar wick noise while also preventing AVG or
    previous-bar requirements from delaying a valid configured entry.
    """
    session_date: str | None = None
    for row in values:
        match = sheets._SESSION_HEADER.match(str(row[0] if row else "").strip())
        if match:
            session_date = match.group(1)
    if session_date is None:
        return None

    normalized_now = (
        now.replace(tzinfo=timezone.utc)
        if now.tzinfo is None
        else now.astimezone(timezone.utc)
    )
    local_now = normalized_now.astimezone(_INDIA)
    try:
        if local_now.date() != date.fromisoformat(session_date):
            return None
        snapshot = parse_signal_snapshot(
            values,
            target_date=date.fromisoformat(session_date),
        )
    except Exception:
        logger.exception("Base-trigger Sheet snapshot parse failed.")
        return None

    if snapshot is None or not snapshot.latest_slot:
        return None
    active_session = session_for_slot(snapshot.latest_slot)
    if active_session not in {"morning", "evening"}:
        return None

    buy_base = snapshot.buy_base
    sell_base = snapshot.sell_base
    session_high = snapshot.day_high
    session_low = snapshot.day_low
    if (
        buy_base is None
        or sell_base is None
        or session_high is None
        or session_low is None
    ):
        return None

    triggers: list[tuple[datetime, str]] = []
    in_current_block = False
    for row in values:
        first = str(row[0] if row else "").strip()
        header = sheets._SESSION_HEADER.match(first)
        if header:
            in_current_block = header.group(1) == session_date
            continue
        if not in_current_block or len(row) < 6:
            continue

        bounds = _slot_bounds(sheets, first, session_date=session_date)
        if bounds is None:
            continue
        _, closed_at, row_session = bounds
        if row_session != active_session or normalized_now < closed_at:
            continue

        high = _decimal(row[1])
        low = _decimal(row[2])
        live_price = _decimal(row[5])
        if high is None or low is None or live_price is None:
            continue

        buy_cross = low <= buy_base <= high and live_price > buy_base
        sell_cross = low <= sell_base <= high and live_price < sell_base
        if buy_cross == sell_cross:
            # Neither side crossed, or both bases were swept in one bar. In the
            # latter case leave direction to the existing structure/Shadow path.
            continue
        triggers.append((closed_at, "BUY" if buy_cross else "SELL"))

    if not triggers:
        return None

    confirmed_at, direction = min(triggers, key=lambda item: item[0])
    entry = buy_base if direction == "BUY" else sell_base
    stop_loss = session_low if direction == "BUY" else session_high
    if (direction == "BUY" and stop_loss >= entry) or (
        direction == "SELL" and stop_loss <= entry
    ):
        return None

    raw_targets = list(
        snapshot.buy_targets if direction == "BUY" else snapshot.sell_targets
    )
    selected = sheets._select_analysis_targets(
        direction=direction,
        entry_price=entry,
        raw_targets=raw_targets,
        fallback_high=session_high,
        fallback_low=session_low,
    )
    if selected is None:
        return None

    target, targets, target_slots = selected
    analysis_worksheet = getattr(
        sheets, "_ANALYSIS_WORKSHEET", GoogleSheetsService._ANALYSIS_WORKSHEET
    )
    return SheetSignal(
        direction=direction,
        target_price=target,
        stop_loss=stop_loss,
        label=(
            f"{session_date} {active_session.upper()} SESSION · "
            f"{direction} Base closed-bar trigger"
        ),
        external_key=f"gsheet-session:{session_date}:{active_session}:{direction}",
        reference_price=entry,
        observed_at=confirmed_at,
        source=f"GOOGLE_SHEET:{analysis_worksheet}",
        targets=targets,
        target_slots=target_slots,
    )


def _structural_override_signal(
    sheets: GoogleSheetsService,
    values: list[list[object]],
    *,
    now: datetime,
) -> SheetSignal | None:
    """Build a Sheet-owned candidate when two closed structural breaks confirm.

    This uses only canonical Sheet values: active session Buy/Sell Base,
    session high/low for risk, and the configured Target 1..6 table. It does
    not invent or extrapolate levels.
    """
    session_date: str | None = None
    for row in values:
        match = sheets._SESSION_HEADER.match(str(row[0] if row else "").strip())
        if match:
            session_date = match.group(1)
    if session_date is None:
        return None

    try:
        snapshot = parse_signal_snapshot(
            values,
            target_date=date.fromisoformat(session_date),
        )
    except Exception:
        logger.exception("Structural Sheet snapshot parse failed.")
        return None

    if snapshot is None or not snapshot.latest_slot:
        return None
    session_name = session_for_slot(snapshot.latest_slot)
    if session_name not in {"morning", "evening"}:
        return None

    structure = latest_two_bar_break(
        values,
        signal_date=session_date,
        session_name=session_name,
        now=now,
    )
    if structure is None:
        return None

    direction, confirmed_at = structure
    entry = snapshot.buy_base if direction == "BUY" else snapshot.sell_base
    session_high = snapshot.day_high
    session_low = snapshot.day_low
    if entry is None or session_high is None or session_low is None:
        return None

    stop_loss = session_low if direction == "BUY" else session_high
    if (direction == "BUY" and stop_loss >= entry) or (
        direction == "SELL" and stop_loss <= entry
    ):
        return None

    raw_targets = list(
        snapshot.buy_targets if direction == "BUY" else snapshot.sell_targets
    )
    selected = sheets._select_analysis_targets(
        direction=direction,
        entry_price=entry,
        raw_targets=raw_targets,
        fallback_high=session_high,
        fallback_low=session_low,
    )
    if selected is None:
        return None

    target, targets, target_slots = selected
    analysis_worksheet = getattr(
        sheets, "_ANALYSIS_WORKSHEET", GoogleSheetsService._ANALYSIS_WORKSHEET
    )
    return SheetSignal(
        direction=direction,
        target_price=target,
        stop_loss=stop_loss,
        label=(
            f"{session_date} {session_name.upper()} SESSION · "
            f"two closed {'higher highs' if direction == 'BUY' else 'lower lows'}"
        ),
        external_key=f"gsheet-session:{session_date}:{session_name}:{direction}",
        reference_price=entry,
        observed_at=confirmed_at,
        source=f"GOOGLE_SHEET:{analysis_worksheet}",
        targets=targets,
        target_slots=target_slots,
    )


def load_authoritative_sheet_signal(
    sheets: GoogleSheetsService,
    *,
    now: datetime | None = None,
) -> SheetSignal | None:
    """Return the delivery-authoritative Sheet signal."""
    normalized_now = now or datetime.now(timezone.utc)

    try:
        values = sheets._analysis_values()
    except Exception:
        logger.exception(
            "Canonical Google Sheet analysis read failed; signal creation blocked."
        )
        return None

    has_canonical_sessions = any(
        sheets._SESSION_HEADER.match(str(row[0] if row else "").strip())
        for row in values
    )

    if has_canonical_sessions:
        base_trigger = _base_cross_signal(
            sheets,
            values,
            now=normalized_now,
        )
        if base_trigger is not None:
            return base_trigger

        structural = _structural_override_signal(
            sheets,
            values,
            now=normalized_now,
        )
        if structural is not None:
            return structural

        try:
            signal = sheets.parse_latest_analysis_signal(
                values,
                now=normalized_now,
                max_age=sheets._MAX_ANALYSIS_AGE,
            )
        except Exception:
            logger.exception(
                "Canonical Google Sheet analysis parse failed; signal creation blocked."
            )
            return None

        if signal is None:
            logger.warning(
                "Canonical Google Sheet session exists but has no fresh valid signal; "
                "legacy structured-row fallback suppressed."
            )
        return signal

    return sheets.get_latest_signal()
