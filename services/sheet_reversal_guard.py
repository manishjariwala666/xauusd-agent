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


def _closed_session_rows(
    values: list[list[Any]],
    *,
    signal_date: str,
    session_name: str,
    now: datetime,
) -> list[tuple[Decimal, Decimal, Decimal | None, Decimal, Decimal]]:
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
        if start is not None and (
            first.startswith("DATE:") or first.startswith("XAUUSD SESSION ")
        ):
            end = index
            break
    if start is None:
        return []

    rows: list[tuple[Decimal, Decimal, Decimal | None, Decimal, Decimal]] = []
    for raw in values[start:end]:
        cells = [str(cell).strip() for cell in raw]
        if len(cells) < 6 or _session_for_slot(cells[0]) != session_name:
            continue
        high = _decimal(cells[1])
        low = _decimal(cells[2])
        prev_avg = _decimal(cells[3])
        avg = _decimal(cells[4])
        cmp = _decimal(cells[5])
        closed_at = _slot_close_at(signal_date, cells[0])
        if None in (high, low, avg, cmp) or closed_at is None:
            continue
        if closed_at > normalized_now:
            continue
        rows.append((high, low, prev_avg, avg, cmp))
    return rows


def opposite_reversal_confirmed(
    values: list[list[Any]],
    *,
    signal_date: str,
    session_name: str,
    from_direction: str,
    to_direction: str,
    now: datetime,
) -> bool:
    """Confirm an opposite signal only after two structural breaks.

    SELL -> BUY requires the latest three closed bars to form two consecutive
    higher highs and the latest bar to confirm bullish AVG/CMP structure.
    BUY -> SELL requires two consecutive lower lows and bearish AVG/CMP.
    """
    source = from_direction.strip().upper()
    target = to_direction.strip().upper()
    if source == target or {source, target} != {"BUY", "SELL"}:
        return source == target

    rows = _closed_session_rows(
        values,
        signal_date=signal_date,
        session_name=session_name,
        now=now,
    )
    if len(rows) < 3:
        return False

    older = rows[-3]
    previous = rows[-2]
    latest = rows[-1]
    high, low, sheet_prev_avg, avg, cmp = latest
    prev_high, prev_low, _prev_sheet_avg, prev_avg, _prev_cmp = previous
    older_high, older_low, *_ = older
    comparison_avg = sheet_prev_avg if sheet_prev_avg is not None else prev_avg

    if source == "SELL" and target == "BUY":
        bullish = avg > comparison_avg and cmp > avg
        return bullish and high > prev_high > older_high

    bearish = avg < comparison_avg and cmp < avg
    return bearish and low < prev_low < older_low


def signal_identity(signal: dict[str, Any]) -> tuple[str, str] | None:
    external_key = str(signal.get("external_key") or "")
    parts = external_key.split(":")
    if len(parts) >= 4 and parts[0] == "gsheet-session":
        session = parts[2].lower()
        if session in {"morning", "evening"}:
            return parts[1], session
    return None
