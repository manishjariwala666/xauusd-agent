"""Authoritative Google Sheet source selection for outbound signals.

The canonical analysis worksheet owns delivery whenever DATE:/XAUUSD SESSION
blocks are present. This prevents an older structured BUY/SELL row from
silently overriding repaired session entry/SL/TP values used by Telegram and
WhatsApp.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from loguru import logger

from services.google_sheets import GoogleSheetsService, SheetSignal


def _version_canonical_signal(signal: SheetSignal | None) -> SheetSignal | None:
    """Make canonical session candidates unique per observed setup bar.

    The parser intentionally keeps the stable date/session/direction identity.
    Runtime delivery needs one more component so an earlier blocked candidate
    cannot suppress a later confirmed reversal in the same session.
    """
    if signal is None:
        return None
    if not signal.external_key.startswith("gsheet-session:"):
        return signal
    if signal.observed_at is None:
        return signal
    bar_key = signal.observed_at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return replace(
        signal,
        external_key=f"{signal.external_key}:{bar_key}",
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

    Reversal confirmation is intentionally applied later against the existing
    active persisted signal; it must not prevent the first valid session signal.
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
        return _version_canonical_signal(signal)

    return sheets.get_latest_signal()
