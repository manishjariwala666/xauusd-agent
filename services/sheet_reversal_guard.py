"""Two-bar structural reversal confirmation for Sheet-driven XAUUSD signals."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo


_INDIA = ZoneInfo("Asia/Kolkata")


def _decimal(value: Any) -> Decimal | None:
    text = str(value or "").strip().replace(",", "")
    if not text:
        return None
    try:
        parsed = Decimal(text)
    except InvalidOperation:
        return None
    return parsed if parsed.is_finite() else None


def _session_for_slot(label: str) -> str | None:
    text = label.strip().upper()
    if " TO " not in text:
        return None
    start = text.split(" TO ", 1)[0].strip()
    try:
        parsed = datetime.strptime(start, "%I:%M %p")
    except ValueError:
        return None
    minutes = parsed.hour * 60 + parsed.minute
    if 210 <= minutes < 870:
        return "morning"
    if minutes >= 870 or minutes <= 150:
        return "evening"
    return None


def _slot_close_at(signal_date: str, label: str) -> datetime | None:
    text = label.strip().upper()
    if " TO " not in text:
        return None
    start_text, end_text = [part.strip() for part in text.split(" TO ", 1)]
    try:
        start_time = datetime.strptime(start_text, "%I:%M %p")
        end_time = datetime.strptime(end_text, "%I:%M %p")
        start = datetime.strptime(signal_date, "%Y-%m-%d").replace(
            hour=start_time.hour,
            minute=start_time.minute,
            tzinfo=_INDIA,
        )
        end = start.replace(hour=end_time.hour, minute=end_time.minute)
    except ValueError:
        return None
    if end <= start:
        end += timedelta(days=1)
    return end.astimezone(timezone.utc)


def confirmed_session_direction(
    values: list[list[Any]],
    *,
    signal_date: str,
    session_name: str,
    now: datetime,
) -> str | None:
    """Return BUY/SELL only after reversal has two-bar structure confirmation.

    First directional setup may establish the session bias. Once established,
    SELL -> BUY requires two consecutive higher highs plus bullish AVG/CMP
    confirmation. BUY -> SELL requires two consecutive lower lows plus bearish
    AVG/CMP confirmation. A one-bar bounce/dip cannot flip the active bias.
    """
    normalized_now = (
        now.replace(tzinfo=timezone.utc)
        if now.tzinfo is None
        else now.astimezone(timezone.utc)
    )

    start: int | None = None
    end = len(values)
    marker_a = f"DATE: {signal_date}".upper()
    marker_b = f"XAUUSD SESSION {signal_date}".upper()
    for index, row in enumerate(values):
        first = str(row[0] if row else "").strip().upper()
        if start is None and first in {marker_a, marker_b}:
            start = index + 1
            continue
        if start is not None and (first.startswith("DATE:") or first.startswith("XAUUSD SESSION ")):
            end = index
            break
    if start is None:
        return None

    rows: list[tuple[Decimal, Decimal, Decimal, Decimal, datetime]] = []
    for raw in values[start:end]:
        cells = [str(cell).strip() for cell in raw]
        if len(cells) < 6:
            continue
        slot = cells[0]
        if _session_for_slot(slot) != session_name:
            continue
        high = _decimal(cells[1])
        low = _decimal(cells[2])
        sheet_prev_avg = _decimal(cells[3])
        avg = _decimal(cells[4])
        cmp = _decimal(cells[5])
        closed_at = _slot_close_at(signal_date, slot)
        if None in (high, low, avg, cmp) or closed_at is None:
            continue
        if closed_at > normalized_now:
            continue
        rows.append((high, low, sheet_prev_avg or avg, avg, cmp))

    if len(rows) < 2:
        return None

    active: str | None = None
    for index in range(1, len(rows)):
        high, low, sheet_prev_avg, avg, cmp = rows[index]
        prev_high, prev_low, _prev_sheet_avg, prev_avg, _prev_cmp = rows[index - 1]
        comparison_avg = sheet_prev_avg if sheet_prev_avg is not None else prev_avg

        bullish = high > prev_high and avg > comparison_avg and cmp > avg
        bearish = low < prev_low and avg < comparison_avg and cmp < avg

        candidate: str | None = "BUY" if bullish else "SELL" if bearish else None
        if candidate is None:
            continue
        if active is None or candidate == active:
            active = candidate
            continue

        if index < 2:
            continue
        older_high, older_low, *_ = rows[index - 2]

        if active == "SELL" and candidate == "BUY":
            if high > prev_high > older_high:
                active = "BUY"
        elif active == "BUY" and candidate == "SELL":
            if low < prev_low < older_low:
                active = "SELL"

    return active


def signal_identity(signal: dict[str, Any]) -> tuple[str, str] | None:
    external_key = str(signal.get("external_key") or "")
    parts = external_key.split(":")
    if len(parts) >= 4 and parts[0] == "gsheet-session":
        session = parts[2].lower()
        if session in {"morning", "evening"}:
            return parts[1], session
    return None
