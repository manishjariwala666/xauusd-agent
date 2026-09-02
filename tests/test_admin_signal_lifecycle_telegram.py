"""Regression coverage for ADMIN CANCEL/CLOSE Telegram mirroring."""

import inspect

import pytest

from services import admin_signals_service
from services.admin_signal_lifecycle_telegram import (
    TERMINAL_TELEGRAM_ACTIONS,
    format_admin_terminal_lifecycle_message,
)


def test_terminal_action_scope_is_cancel_and_close_only() -> None:
    assert TERMINAL_TELEGRAM_ACTIONS == {"CANCEL", "CLOSE"}


@pytest.mark.parametrize(
    ("action", "status", "marker"),
    [("CANCEL", "CANCELLED", "🚫"), ("CLOSE", "CLOSED", "✅")],
)
def test_terminal_message_uses_canonical_saved_state(
    action: str,
    status: str,
    marker: str,
) -> None:
    message = format_admin_terminal_lifecycle_message(
        {
            "symbol": "XAUUSD",
            "timeframe": "INTRADAY",
            "outcome": "MANUAL_OWNER_ACTION",
            "result_points": "12.5" if action == "CLOSE" else None,
            "public_id": "signal-public-id",
        },
        action=action,
    )
    assert f"{marker} XAUUSD SIGNAL {status}" in message
    assert f"Status: {status}" in message
    assert "Timeframe: INTRADAY" in message
    assert "Outcome: MANUAL_OWNER_ACTION" in message
    assert "Signal ID: signal-public-id" in message
    assert "Canonical status updated on VenusRealm." in message
    if action == "CLOSE":
        assert "Result: 12.5 points" in message


def test_unsupported_terminal_action_is_rejected() -> None:
    with pytest.raises(ValueError):
        format_admin_terminal_lifecycle_message({"symbol": "XAUUSD"}, action="EXPIRE")


def test_admin_transition_delivers_only_after_canonical_row_reload() -> None:
    source = inspect.getsource(admin_signals_service.transition_admin_signal)
    reload_position = source.index("result = _row(signal_id)")
    delivery_position = source.index("deliver_admin_terminal_lifecycle_telegram")
    assert reload_position < delivery_position
    assert "if action in TERMINAL_TELEGRAM_ACTIONS" in source
    assert "return result" in source
