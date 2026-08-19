"""Production agent facade with durable primary-signal delivery.

The historical implementations remain in ``production_agents_legacy`` while
this facade owns the repaired delivery wiring. Runtime dependencies are synced
before delegated execution so tests, admin overrides, and dependency injection
continue to target ``services.production_agents`` exactly as before.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from services import production_agents_legacy as _legacy
from services.signal_channel_delivery import deliver_pending_signal_recipients


globals().update(
    {
        name: value
        for name, value in vars(_legacy).items()
        if not name.startswith("__")
    }
)


_RUNTIME_SYNC_NAMES = (
    "AIProvider", "session_scope", "save_content", "get_site_setting",
    "get_settings", "create_client", "WhatsAppService", "TelegramService",
    "GoogleSheetsService", "MarketDataService", "run_pipeline_once",
    "format_signal_message", "logger",
)

_LEGACY_STOP_MONITOR = _legacy._monitor_stop_loss_hits


def _sync_legacy_runtime() -> None:
    """Keep facade monkeypatch/dependency injection behavior backward-compatible."""
    for name in _RUNTIME_SYNC_NAMES:
        if name in globals():
            setattr(_legacy, name, globals()[name])
    for name in (
        "_blog_publish_default", "_fallback_blog_payload",
        "_valid_long_form_blog", "_normalize_public_blog_sections",
    ):
        value = globals().get(name)
        if value is not None and value is not globals().get("run_blog_agent"):
            setattr(_legacy, name, value)


def _legacy_sheet_signal_is_superseded(signal: dict[str, Any]) -> tuple[bool, str]:
    external_key = str(signal.get("external_key") or "").strip()
    if not external_key.startswith("gsheet:"):
        return False, ""
    try:
        sheets = GoogleSheetsService()
        values = sheets._analysis_values()
    except Exception:
        return True, "Legacy Google Sheet signal blocked because canonical source verification is unavailable."
    has_canonical_sessions = any(
        sheets._SESSION_HEADER.match(str(row[0] if row else "").strip())
        for row in values
    )
    if has_canonical_sessions:
        return True, "Legacy Google Sheet signal is superseded by canonical session SL/TP data."
    return False, ""


def _two_bar_delivery_reversal_confirmed(signal: dict[str, Any]) -> bool:
    """Verify candidate against the previous opposite signal from the trading day."""
    from services.sheet_reversal_guard import opposite_reversal_confirmed, signal_identity

    identity = signal_identity(signal)
    signal_id = signal.get("id")
    candidate = str(signal.get("signal_type") or "").strip().upper()
    if identity is None or signal_id is None or candidate not in {"BUY", "SELL"}:
        return False

    signal_date, session_name = identity
    prefix = f"gsheet-session:{signal_date}:%"
    opposite = "SELL" if candidate == "BUY" else "BUY"
    try:
        with session_scope() as session:
            previous = (
                session.execute(
                    text(
                        """
                        SELECT signal_type
                        FROM public.market_signals
                        WHERE id <> :id
                          AND external_key LIKE :prefix
                          AND signal_type = :opposite
                        ORDER BY signal_time DESC
                        LIMIT 1
                        """
                    ),
                    {
                        "id": signal_id,
                        "prefix": prefix,
                        "opposite": opposite,
                    },
                )
                .mappings()
                .first()
            )
    except Exception:
        logger.exception("Prior Sheet signal lookup failed; sweep override disabled.")
        return False

    if previous is None:
        return False

    try:
        values = GoogleSheetsService()._analysis_values()
        return opposite_reversal_confirmed(
            values,
            signal_date=signal_date,
            session_name=session_name,
            from_direction=opposite,
            to_direction=candidate,
            now=datetime.now(timezone.utc),
        )
    except Exception:
        logger.exception("Two-bar reversal verification failed; sweep override disabled.")
        return False


def _captain_delivery_verifier(signal: dict[str, Any]) -> tuple[bool, str]:
    superseded, source_reason = _legacy_sheet_signal_is_superseded(signal)
    if superseded:
        return False, source_reason
    from services.captain_shadow_gate import evaluate_signal_shadow_gate
    reversal_confirmed = _two_bar_delivery_reversal_confirmed(signal)
    if reversal_confirmed:
        result = evaluate_signal_shadow_gate(
            signal,
            structure_reversal_confirmed=True,
        )
    else:
        # Preserve compatibility for the common path and older test/detour
        # callables that implement the original single-argument gate contract.
        result = evaluate_signal_shadow_gate(signal)
    if not result.blocked:
        return True, result.reason
    return False, (
        f"decision={result.decision}; direction={result.direction}; "
        f"confidence={result.confidence}; macro_bias={result.macro_bias}; "
        f"news_locked={result.news_locked}; reason={result.reason}"
    )


def _durable_pending_whatsapp_signals() -> None:
    _sync_legacy_runtime()
    now = datetime.now(timezone.utc)
    if now.weekday() >= 5:
        logger.info("WhatsApp signal delivery paused for the weekend")
        return
    recipients = _legacy._verified_whatsapp_recipients()
    if not recipients:
        logger.info("WhatsApp signal delivery skipped: no verified recipients")
        return
    service = _legacy.WhatsAppService()
    delivered, failed = deliver_pending_signal_recipients(
        channel="whatsapp",
        recipients=recipients,
        send=service.send_text,
        format_message=_legacy.format_signal_message,
        max_attempts=3,
        verify_signal=_captain_delivery_verifier,
    )
    if delivered or failed:
        logger.info("Primary WhatsApp delivery completed: delivered={} failed={}", delivered, failed)


def _durable_telegram_broadcast(telegram: Any, limit: int = 50) -> int:
    del limit
    from services.telegram_primary_delivery import deliver_pending_telegram_signals
    delivered, failed = deliver_pending_telegram_signals(telegram)
    if delivered or failed:
        logger.info("Primary Telegram delivery completed: delivered={} failed={}", delivered, failed)
    return delivered


def _guarded_stop_loss_monitor(*, market_data: Any, telegram: Any) -> int:
    """Close canonical Sheet SL only after opposite two-bar structure confirms."""
    from services.master_ai_signal_reader import parse_signal_snapshot
    from services.sheet_reversal_guard import (
        opposite_reversal_confirmed,
        session_for_slot,
        signal_identity,
    )

    try:
        with session_scope() as session:
            row = (
                session.execute(
                    text(
                        """
                        SELECT *
                        FROM public.market_signals
                        WHERE signal_type IN ('BUY', 'SELL')
                          AND external_key LIKE 'gsheet-session:%'
                          AND COALESCE(status, '') NOT IN ('STOPPED', 'COMPLETED', 'CANCELLED')
                        ORDER BY signal_time DESC
                        LIMIT 1
                        """
                    )
                )
                .mappings()
                .first()
            )
    except Exception:
        logger.exception("Sheet stop monitor lookup failed closed")
        return 0

    if not row:
        return _LEGACY_STOP_MONITOR(market_data=market_data, telegram=telegram)

    signal = dict(row)
    identity = signal_identity(signal)
    if identity is None:
        return 0
    signal_date, original_session = identity
    try:
        values = GoogleSheetsService()._analysis_values()
        snapshot = parse_signal_snapshot(values, signal_date=date.fromisoformat(signal_date))
        current_session = (
            session_for_slot(snapshot.latest_slot)
            if snapshot is not None and snapshot.latest_slot
            else None
        ) or original_session
        confirmed = opposite_reversal_confirmed(
            values,
            signal_date=signal_date,
            session_name=current_session,
            from_direction=str(signal.get("signal_type") or "").upper(),
            to_direction=("BUY" if str(signal.get("signal_type") or "").upper() == "SELL" else "SELL"),
            now=datetime.now(timezone.utc),
        )
    except Exception:
        logger.exception("Sheet stop reversal verification failed closed")
        return 0
    if not confirmed:
        logger.info("Sheet stop monitor waiting for opposite two-bar reversal")
        return 0
    return _LEGACY_STOP_MONITOR(market_data=market_data, telegram=telegram)


def run_signal_agent(payload: dict[str, Any]) -> str:
    _sync_legacy_runtime()
    return _legacy.run_signal_agent(payload)


def run_whatsapp_reply_agent(payload: dict[str, Any]) -> str:
    _sync_legacy_runtime()
    return _legacy.run_whatsapp_reply_agent(payload)


def run_telegram_reply_agent(payload: dict[str, Any]) -> str:
    _sync_legacy_runtime()
    return _legacy.run_telegram_reply_agent(payload)


def run_blog_agent(payload: dict[str, Any]) -> str:
    _sync_legacy_runtime()
    return _legacy.run_blog_agent(payload)


def run_image_agent(payload: dict[str, Any]) -> str:
    _sync_legacy_runtime()
    return _legacy.run_image_agent(payload)


def run_announcement_agent(payload: dict[str, Any]) -> str:
    _sync_legacy_runtime()
    return _legacy.run_announcement_agent(payload)


def run_seo_agent(payload: dict[str, Any]) -> str:
    _sync_legacy_runtime()
    return _legacy.run_seo_agent(payload)


RUNNERS = dict(_legacy.RUNNERS)
RUNNERS.update(
    {
        "signal_agent": run_signal_agent,
        "whatsapp_reply_agent": run_whatsapp_reply_agent,
        "telegram_reply_agent": run_telegram_reply_agent,
        "ai_blog_agent": run_blog_agent,
        "image_agent": run_image_agent,
        "announcement_agent": run_announcement_agent,
        "seo_agent": run_seo_agent,
    }
)
