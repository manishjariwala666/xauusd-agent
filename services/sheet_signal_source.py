"""Authoritative Google Sheet source selection for outbound signals.

The canonical analysis worksheet owns delivery whenever DATE:/XAUUSD SESSION
blocks are present. This prevents an older structured BUY/SELL row from
silently overriding repaired session entry/SL/TP values used by Telegram and
WhatsApp.
"""

from __future__ import annotations

from datetime import datetime, timezone

from loguru import logger

from services.google_sheets import GoogleSheetsService, SheetSignal
from services.sheet_reversal_guard import (
    confirmed_session_direction,
    signal_identity,
)


def load_authoritative_sheet_signal(
    sheets: GoogleSheetsService,
    *,
    now: datetime | None = None,
) -> SheetSignal | None:
    """Return the delivery-authoritative Sheet signal.

    When the canonical analysis worksheet contains session blocks, it is the
    sole source of truth. If that worksheet has no fresh valid candidate we
    fail closed instead of falling back to a legacy structured row that may
    carry stale or mismatched SL/TP values.

    A canonical candidate must also match the two-bar confirmed session bias.
    This prevents a one-candle pullback or base recross from flipping an active
    SELL into BUY (or vice versa).

    Legacy ``get_latest_signal`` remains available only for deployments whose
    analysis worksheet contains no canonical session blocks at all.
    """
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
            return None

        identity = signal_identity({"external_key": signal.external_key})
        if identity is None:
            logger.warning(
                "Canonical Sheet candidate lacks session identity; signal blocked."
            )
            return None

        signal_date, session_name = identity
        confirmed = confirmed_session_direction(
            values,
            signal_date=signal_date,
            session_name=session_name,
            now=normalized_now,
        )
        if confirmed != signal.direction:
            logger.warning(
                "Canonical Sheet candidate blocked by reversal guard: "
                "candidate={} confirmed={} date={} session={}",
                signal.direction,
                confirmed,
                signal_date,
                session_name,
            )
            return None

        return signal

    # Backward compatibility for installations that genuinely use only the
    # legacy structured signal worksheet and have no canonical session blocks.
    return sheets.get_latest_signal()
