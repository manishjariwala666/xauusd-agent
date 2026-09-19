"""Weekday Morning/Evening XAUUSD session setup delivery for WhatsApp."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal
import hashlib
from typing import Any, Callable, Iterable
from zoneinfo import ZoneInfo

from loguru import logger
from sqlalchemy import text

from core.database import session_scope
from services.google_sheets import GoogleSheetsService
from services.sheet_signal_source import _session_context_from_values


_INDIA = ZoneInfo("Asia/Kolkata")
_SESSION_STARTS = {
    "morning": time(3, 30),
    "evening": time(14, 30),
}


@dataclass(frozen=True)
class SessionSetup:
    signal_date: str
    session_name: str
    direction: str
    entry: Decimal
    stop_loss: Decimal
    targets: tuple[Decimal, ...]


def _latest_session_date(
    sheets: GoogleSheetsService,
    values: list[list[object]],
) -> str | None:
    session_date: str | None = None
    for row in values:
        match = sheets._SESSION_HEADER.match(str(row[0] if row else "").strip())
        if match:
            session_date = match.group(1)
    return session_date


def load_due_session_setups(
    sheets: GoogleSheetsService,
    *,
    now: datetime | None = None,
) -> list[SessionSetup]:
    """Return the four configured session/direction setups when each session is due.

    The Google Sheet remains authoritative. No target is invented or extrapolated.
    A setup is eligible only on the matching India trading date, Monday-Friday,
    after that session's configured start time, and only when all six sequential
    directionally valid targets exist.
    """
    current = now or datetime.now(timezone.utc)
    normalized = (
        current.replace(tzinfo=timezone.utc)
        if current.tzinfo is None
        else current.astimezone(timezone.utc)
    )
    local_now = normalized.astimezone(_INDIA)
    if local_now.weekday() >= 5:
        return []

    values = sheets._analysis_values()
    signal_date = _latest_session_date(sheets, values)
    if signal_date is None:
        return []

    try:
        parsed_date = date.fromisoformat(signal_date)
    except ValueError:
        return []
    if parsed_date != local_now.date():
        return []

    setups: list[SessionSetup] = []
    for session_name in ("morning", "evening"):
        session_start = datetime.combine(
            parsed_date,
            _SESSION_STARTS[session_name],
            tzinfo=_INDIA,
        )
        if local_now < session_start:
            continue

        context = _session_context_from_values(
            sheets,
            values,
            session_date=signal_date,
            session_name=session_name,
        )
        if context is None:
            continue

        (
            session_high,
            session_low,
            buy_base,
            sell_base,
            buy_targets,
            sell_targets,
        ) = context

        for direction, entry, stop_loss, raw_targets in (
            ("BUY", buy_base, session_low, buy_targets),
            ("SELL", sell_base, session_high, sell_targets),
        ):
            selected = sheets._select_analysis_targets(
                direction=direction,
                entry_price=entry,
                raw_targets=list(raw_targets),
                fallback_high=session_high,
                fallback_low=session_low,
            )
            if selected is None:
                continue
            _, _, target_slots = selected
            targets = tuple(value for value in target_slots[:6] if value is not None)
            if len(targets) != 6:
                logger.warning(
                    "Session setup blocked: incomplete T1-T6 date={} session={} direction={}",
                    signal_date,
                    session_name,
                    direction,
                )
                continue

            setups.append(
                SessionSetup(
                    signal_date=signal_date,
                    session_name=session_name,
                    direction=direction,
                    entry=entry,
                    stop_loss=stop_loss,
                    targets=targets,
                )
            )

    return setups


def _price(value: Decimal) -> str:
    rendered = f"{value:.2f}"
    return rendered.rstrip("0").rstrip(".")


def format_session_setup_message(setup: SessionSetup) -> str:
    """Render one of four professional Morning/Evening BUY/SELL message styles."""
    session = setup.session_name.upper()
    direction = setup.direction.upper()

    headers = {
        ("morning", "BUY"): "🌅🟢 XAUUSD MORNING BUY SIGNAL 🟢🌅",
        ("morning", "SELL"): "🌅🔴 XAUUSD MORNING SELL SIGNAL 🔴🌅",
        ("evening", "BUY"): "🌆🟢 XAUUSD EVENING BUY SIGNAL 🟢🌆",
        ("evening", "SELL"): "🌆🔴 XAUUSD EVENING SELL SIGNAL 🔴🌆",
    }
    header = headers[(setup.session_name, direction)]

    lines = [
        header,
        "",
        f"📅 Date: {setup.signal_date}",
        f"📍 Session: {session} SESSION",
        f"⚡ {direction} Base: {_price(setup.entry)}",
        "",
        "🎯 PROFIT TARGETS",
    ]
    target_icons = ("1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣")
    for number, (icon, target) in enumerate(
        zip(target_icons, setup.targets),
        start=1,
    ):
        suffix = " 🏆" if number == 6 else ""
        lines.append(f"{icon} Target {number}: {_price(target)}{suffix}")

    lines.extend(
        [
            "",
            f"🛡️ Risk Reference / SL: {_price(setup.stop_loss)}",
            "💰 Profit Book: follow your own risk and position-management plan.",
            "✨ Trade with discipline. Protect capital first.",
            "",
            "🎉💚 Enjoy Profit from VenusRealm 💚🎉",
            "📊 Market analysis only — returns are not guaranteed.",
            "— VenusRealm",
        ]
    )
    return "\n".join(lines)


def _delivery_key(setup: SessionSetup, recipient: str) -> str:
    recipient_hash = hashlib.sha256(recipient.encode("utf-8")).hexdigest()[:16]
    return (
        "wa_session_setup:"
        f"{setup.signal_date}:{setup.session_name}:{setup.direction}:{recipient_hash}"
    )


def _claim_delivery(key: str) -> bool:
    """Atomically claim a setup delivery using the existing protected settings table."""
    try:
        with session_scope() as session:
            inserted = session.execute(
                text(
                    """
                    INSERT INTO public.site_settings (
                        setting_key, setting_value, is_sensitive
                    )
                    VALUES (:key, 'CLAIMED', TRUE)
                    ON CONFLICT (setting_key) DO NOTHING
                    RETURNING setting_key
                    """
                ),
                {"key": key},
            ).scalar_one_or_none()
            if inserted:
                return True

            retried = session.execute(
                text(
                    """
                    UPDATE public.site_settings
                    SET setting_value = 'CLAIMED',
                        updated_at = NOW()
                    WHERE setting_key = :key
                      AND (
                          setting_value LIKE 'FAILED:%'
                          OR (
                              setting_value = 'CLAIMED'
                              AND updated_at < NOW() - INTERVAL '5 minutes'
                          )
                      )
                    RETURNING setting_key
                    """
                ),
                {"key": key},
            ).scalar_one_or_none()
            return bool(retried)
    except Exception as exc:
        logger.warning(
            "Session setup delivery claim failed closed: category={}",
            exc.__class__.__name__,
        )
        return False


def _finish_delivery(
    key: str,
    *,
    message_id: str | None,
    error_category: str | None,
) -> None:
    value = (
        f"SENT:{message_id or 'accepted'}"
        if error_category is None
        else f"FAILED:{error_category}"
    )
    with session_scope() as session:
        session.execute(
            text(
                """
                UPDATE public.site_settings
                SET setting_value = :value,
                    updated_at = NOW()
                WHERE setting_key = :key
                """
            ),
            {"key": key, "value": value[:1000]},
        )


def deliver_due_session_setup_messages(
    *,
    recipients: Iterable[str],
    send: Callable[[str, str], Any],
    now: datetime | None = None,
) -> tuple[int, int]:
    """Send each due Morning/Evening BUY/SELL setup exactly once per recipient."""
    clean_recipients = list(
        dict.fromkeys(
            str(value).strip()
            for value in recipients
            if str(value).strip()
        )
    )
    if not clean_recipients:
        return 0, 0

    try:
        sheets = GoogleSheetsService()
        setups = load_due_session_setups(sheets, now=now)
    except Exception as exc:
        logger.warning(
            "Session setup source unavailable; delivery skipped: category={}",
            exc.__class__.__name__,
        )
        return 0, 0

    delivered = 0
    failed = 0
    for setup in setups:
        message = format_session_setup_message(setup)
        for recipient in clean_recipients:
            key = _delivery_key(setup, recipient)
            if not _claim_delivery(key):
                continue
            message_id: str | None = None
            error_category: str | None = None
            try:
                result = send(recipient, message)
                if result not in (None, ""):
                    message_id = str(result)[:512]
                delivered += 1
            except Exception as exc:
                error_category = exc.__class__.__name__
                failed += 1
                logger.warning(
                    "Session setup WhatsApp delivery failed: date={} session={} "
                    "direction={} category={}",
                    setup.signal_date,
                    setup.session_name,
                    setup.direction,
                    error_category,
                )
            try:
                _finish_delivery(
                    key,
                    message_id=message_id,
                    error_category=error_category,
                )
            except Exception as exc:
                logger.error(
                    "Session setup delivery finalization failed: category={}",
                    exc.__class__.__name__,
                )

    return delivered, failed
