"""Risk guard for analysis-derived Google Sheet signals.

This layer runs immediately before a Sheet signal is persisted. It never changes
an explicit Sheet SL. For generated/fallback stops it re-validates the exact
session summary available at execution time and adds the Sheet's own
Step×Multiplier volatility buffer. This avoids using a fragile last-candle high
or low when the session extreme is already wider, while preserving closed-bar
signal direction logic in ``GoogleSheetsService``.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re
from typing import Any

from services.google_sheets import SheetSignal


class SignalRiskGuardError(RuntimeError):
    """Raised when a fallback stop cannot be verified safely."""


_DATE_HEADER = re.compile(r"^(?:DATE:\s*|XAUUSD SESSION\s+)(\d{4}-\d{2}-\d{2})$", re.I)


def requires_risk_guard(signal: SheetSignal) -> bool:
    """Return True only for automatically-derived analysis stop losses."""
    label = str(signal.label or "").lower()
    if "sheet buy sl" in label or "sheet sell sl" in label:
        return False
    return any(
        marker in label
        for marker in (
            "recent candle high",
            "recent candle low",
            "session high stop fallback",
            "session low stop fallback",
        )
    )


def protect_sheet_signal(
    signal: SheetSignal,
    values: list[list[Any]],
) -> SheetSignal:
    """Return the signal with a verified, buffered fallback stop.

    Both the recent structural fallback already attached to the signal and the
    session extreme must be on the risk side of entry. If either structure is
    invalid, fail closed instead of allowing one wider extreme to mask it.
    """
    if not requires_risk_guard(signal):
        return signal

    direction = str(signal.direction or "").strip().upper()
    if direction not in {"BUY", "SELL"}:
        raise SignalRiskGuardError("Signal direction is invalid.")
    if signal.reference_price is None:
        raise SignalRiskGuardError("Signal entry price is unavailable.")
    if signal.stop_loss is None:
        raise SignalRiskGuardError("Recent structural stop is unavailable.")

    entry = signal.reference_price
    recent_stop = signal.stop_loss
    if direction == "SELL" and recent_stop <= entry:
        raise SignalRiskGuardError("Recent/session high is invalid for SELL risk.")
    if direction == "BUY" and recent_stop >= entry:
        raise SignalRiskGuardError("Recent/session low is invalid for BUY risk.")

    session_date, session_name = _signal_identity(signal)
    block = _date_block(values, session_date)
    summary = _session_summary(block, session_name)
    if summary is None:
        raise SignalRiskGuardError(
            f"{session_name.title()} session summary is unavailable."
        )

    session_high, session_low, summary_index = summary
    if direction == "SELL":
        if session_high is None or session_high <= entry:
            raise SignalRiskGuardError("Verified session high is invalid for SELL risk.")
        structural_stop = max(recent_stop, session_high)
    else:
        if session_low is None or session_low >= entry:
            raise SignalRiskGuardError("Verified session low is invalid for BUY risk.")
        structural_stop = min(recent_stop, session_low)

    step, multiplier = _target_risk_parameters(block, summary_index, session_name)
    buffer = Decimal("0")
    if step is not None and multiplier is not None and step > 0 and multiplier > 0:
        buffer = step * multiplier

    guarded_stop = (
        structural_stop + buffer
        if direction == "SELL"
        else structural_stop - buffer
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if direction == "SELL" and guarded_stop <= entry:
        raise SignalRiskGuardError("Guarded SELL stop is not above entry.")
    if direction == "BUY" and guarded_stop >= entry:
        raise SignalRiskGuardError("Guarded BUY stop is not below entry.")

    source = "session high" if direction == "SELL" else "session low"
    suffix = f"risk guard: {source}"
    if buffer > 0:
        suffix += f" + {buffer.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)} buffer"

    return replace(
        signal,
        stop_loss=guarded_stop,
        label=f"{signal.label} · {suffix}",
    )


def _signal_identity(signal: SheetSignal) -> tuple[str, str]:
    parts = str(signal.external_key or "").split(":")
    if len(parts) >= 4 and parts[0] == "gsheet-session":
        session_date = parts[1]
        session_name = parts[2].lower()
        if session_name in {"morning", "evening"}:
            return session_date, session_name

    match = re.search(r"(\d{4}-\d{2}-\d{2})", str(signal.label or ""))
    if not match:
        raise SignalRiskGuardError("Signal trading date is unavailable.")
    label = str(signal.label or "").lower()
    session_name = "evening" if "evening" in label else "morning"
    return match.group(1), session_name


def _date_block(values: list[list[Any]], session_date: str) -> list[list[str]]:
    start: int | None = None
    end = len(values)
    for index, raw_row in enumerate(values):
        first = str(raw_row[0] if raw_row else "").strip()
        match = _DATE_HEADER.match(first)
        if not match:
            continue
        if start is not None:
            end = index
            break
        if match.group(1) == session_date:
            start = index + 1
    if start is None:
        raise SignalRiskGuardError(f"Sheet block for {session_date} is unavailable.")
    return [[str(cell).strip() for cell in row] for row in values[start:end]]


def _session_summary(
    rows: list[list[str]],
    session_name: str,
) -> tuple[Decimal | None, Decimal | None, int] | None:
    """Find the exact named summary; explicit session text is authoritative."""
    for index, cells in enumerate(rows):
        lower = [cell.lower() for cell in cells]
        joined = " ".join(lower)
        if f"{session_name} session" not in joined:
            continue
        headers = {cell: pos for pos, cell in enumerate(lower) if cell}
        if "buy base" not in headers or "sell base" not in headers:
            continue
        high_index = headers.get("session high") or headers.get("day high")
        low_index = headers.get("session low") or headers.get("day low")
        if high_index is None or low_index is None or index + 1 >= len(rows):
            continue
        value_row = rows[index + 1]
        high = _decimal_at(value_row, high_index)
        low = _decimal_at(value_row, low_index)
        return high, low, index
    return None


def _target_risk_parameters(
    rows: list[list[str]],
    summary_index: int,
    session_name: str,
) -> tuple[Decimal | None, Decimal | None]:
    """Read Step and Multiplier from the target table owned by this summary."""
    for index in range(summary_index + 1, len(rows)):
        cells = rows[index]
        lower = [cell.lower() for cell in cells]
        joined = " ".join(lower)
        if index > summary_index + 1 and (
            "morning session" in joined or "evening session" in joined
        ) and f"{session_name} session" not in joined:
            break
        if len(lower) < 10:
            continue
        if not (
            len(lower) > 9
            and lower[7] == "target"
            and lower[8] == "buy level"
            and lower[9] == "sell level"
        ):
            continue
        headers = {cell: pos for pos, cell in enumerate(lower) if cell}
        step_index = headers.get("step")
        multiplier_index = headers.get("multiplier")
        if index + 1 >= len(rows):
            return None, None
        target_one = rows[index + 1]
        return (
            _decimal_at(target_one, step_index),
            _decimal_at(target_one, multiplier_index),
        )
    return None, None


def _decimal_at(row: list[str], index: int | None) -> Decimal | None:
    if index is None or index >= len(row):
        return None
    cleaned = str(row[index]).strip().replace(",", "")
    if not cleaned:
        return None
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        return None
    if not value.is_finite() or value <= 0:
        return None
    return value
