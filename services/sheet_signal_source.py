"""Authoritative Google Sheet source selection for outbound signals.

The canonical analysis worksheet owns delivery whenever DATE:/XAUUSD SESSION
blocks are present. This prevents an older structured BUY/SELL row from
silently overriding repaired session entry/SL/TP values used by Telegram and
WhatsApp.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from loguru import logger

from services.google_sheets import GoogleSheetsService, SheetSignal
from services.master_ai_signal_reader import parse_signal_snapshot
from services.sheet_reversal_guard import latest_two_bar_break, session_for_slot


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
        source=f"GOOGLE_SHEET:{sheets._ANALYSIS_WORKSHEET}",
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
