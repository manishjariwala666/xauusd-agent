"""Production agent facade with durable primary-signal delivery.

The historical production-agent implementation is preserved verbatim in
``production_agents_legacy`` so this repair can change only the primary
WhatsApp delivery path. All existing public/private names remain available.
"""

from __future__ import annotations

from datetime import datetime, timezone

from services import production_agents_legacy as _legacy
from services.signal_channel_delivery import deliver_pending_signal_recipients


# Preserve the existing production-agent API surface, including private helpers
# used by tests and internal modules. Dunder module metadata intentionally stays
# owned by this facade.
globals().update(
    {
        name: value
        for name, value in vars(_legacy).items()
        if not name.startswith("__")
    }
)


def _durable_pending_whatsapp_signals() -> None:
    """Deliver primary BUY/SELL messages once per verified recipient."""
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
    )
    if delivered or failed:
        logger.info(
            "Primary WhatsApp delivery completed: delivered={} failed={}",
            delivered,
            failed,
        )


# run_signal_agent is defined in the preserved module. Its global lookup for
# _deliver_pending_whatsapp_signals therefore must be replaced there as well as
# on this facade. This keeps the rest of Signal Agent behavior unchanged.
_legacy._deliver_pending_whatsapp_signals = _durable_pending_whatsapp_signals


def deliver_pending_whatsapp_signals() -> None:
    """Public compatibility entry point for durable WhatsApp signal delivery."""
    _durable_pending_whatsapp_signals()


def _deliver_pending_whatsapp_signals() -> None:
    """Internal compatibility entry point used by existing callers."""
    _durable_pending_whatsapp_signals()
