"""Production agent facade with durable primary-signal delivery.

The historical implementations remain in ``production_agents_legacy`` while
this facade owns the repaired delivery wiring. Runtime dependencies are synced
before delegated execution so tests, admin overrides, and dependency injection
continue to target ``services.production_agents`` exactly as before.
"""

from __future__ import annotations

from datetime import datetime, timezone
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


def _sync_legacy_runtime() -> None:
    """Keep facade monkeypatch/dependency injection behavior backward-compatible."""
    for name in _RUNTIME_SYNC_NAMES:
        if name in globals():
            setattr(_legacy, name, globals()[name])
    for name in (
        "_blog_publish_default", "_fallback_blog_payload",
        "_valid_long_form_blog", "_normalize_public_blog_sections",
        "_verified_whatsapp_recipients",
    ):
        value = globals().get(name)
        if value is not None and value is not globals().get("run_blog_agent"):
            setattr(_legacy, name, value)


def _legacy_sheet_signal_is_superseded(
    signal: dict[str, Any],
) -> tuple[bool, str]:
    """Block old ``gsheet:<hash>`` rows when canonical sessions are active.

    This protects both Telegram and WhatsApp from a previously persisted legacy
    row carrying stale/mismatched SL or TP after the canonical Sheet1 session
    layout became authoritative. Non-Sheet/manual signals are unaffected.
    """
    external_key = str(signal.get("external_key") or "").strip()
    if not external_key.startswith("gsheet:"):
        return False, ""

    try:
        sheets = GoogleSheetsService()
        values = sheets._analysis_values()
    except Exception:
        return True, (
            "Legacy Google Sheet signal blocked because canonical source "
            "verification is unavailable."
        )

    has_canonical_sessions = any(
        sheets._SESSION_HEADER.match(str(row[0] if row else "").strip())
        for row in values
    )
    if has_canonical_sessions:
        return True, (
            "Legacy Google Sheet signal is superseded by canonical session "
            "SL/TP data."
        )
    return False, ""


def _captain_delivery_verifier(signal: dict[str, Any]) -> tuple[bool, str]:
    """Use shared source-integrity + Captain verification for delivery."""
    superseded, source_reason = _legacy_sheet_signal_is_superseded(signal)
    if superseded:
        return False, source_reason

    from services.captain_shadow_gate import evaluate_signal_shadow_gate

    result = evaluate_signal_shadow_gate(signal)
    if not result.blocked:
        return True, result.reason
    return False, (
        f"decision={result.decision}; direction={result.direction}; "
        f"confidence={result.confidence}; macro_bias={result.macro_bias}; "
        f"news_locked={result.news_locked}; reason={result.reason}"
    )


def _durable_pending_whatsapp_signals() -> None:
    """Deliver primary BUY/SELL messages once per verified recipient."""
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
        logger.info(
            "Primary WhatsApp delivery completed: delivered={} failed={}",
            delivered,
            failed,
        )


def _durable_telegram_broadcast(telegram: Any, limit: int = 50) -> int:
    """Route Telegram primary broadcasts through the shared recipient ledger."""
    del limit  # Durable helper owns the bounded pending batch query.
    from services.telegram_primary_delivery import deliver_pending_telegram_signals

    delivered, failed = deliver_pending_telegram_signals(telegram)
    if delivered or failed:
        logger.info(
            "Primary Telegram delivery completed: delivered={} failed={}",
            delivered,
            failed,
        )
    return delivered


_legacy._deliver_pending_whatsapp_signals = _durable_pending_whatsapp_signals


def run_blog_agent(payload: dict[str, Any]) -> str:
    _sync_legacy_runtime()
    return _legacy.run_blog_agent(payload)


def run_image_agent(payload: dict[str, Any]) -> str:
    _sync_legacy_runtime()
    return _legacy.run_image_agent(payload)


def run_signal_agent(payload: dict[str, Any]) -> str:
    _sync_legacy_runtime()
    _legacy._deliver_pending_whatsapp_signals = _durable_pending_whatsapp_signals
    # Signal Agent and the pipeline share the same TelegramService class object;
    # bind its normal broadcast entry point to the durable verified ledger.
    _legacy.TelegramService.broadcast_pending_signals = _durable_telegram_broadcast
    return _legacy.run_signal_agent(payload)


def run_telegram_reply_agent(payload: dict[str, Any]) -> str:
    _sync_legacy_runtime()
    return _legacy.run_telegram_reply_agent(payload)


def run_whatsapp_reply_agent(payload: dict[str, Any]) -> str:
    _sync_legacy_runtime()
    return _legacy.run_whatsapp_reply_agent(payload)


def deliver_pending_whatsapp_signals() -> None:
    _durable_pending_whatsapp_signals()


def _deliver_pending_whatsapp_signals() -> None:
    _durable_pending_whatsapp_signals()


RUNNERS = dict(_legacy.RUNNERS)
RUNNERS.update(
    {
        "ai_blog_agent": run_blog_agent,
        "telegram_reply_agent": run_telegram_reply_agent,
        "whatsapp_reply_agent": run_whatsapp_reply_agent,
        "signal_agent": _master_optional_agent("signal_agent", run_signal_agent),
        "image_agent": _master_optional_agent("image_agent", run_image_agent),
    }
)
