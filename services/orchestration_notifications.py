"""Telegram/admin notifications for Master AI orchestration."""

from __future__ import annotations

from typing import Callable

from services.orchestration_redaction import safe_error_message


class OrchestrationNotificationService:
    """Best-effort notification facade for orchestration lifecycle events.

    The service is intentionally non-fatal: notification failures must never
    fail an orchestration run or expose credentials.
    """

    def __init__(self, *, sender: Callable[[str], None] | None = None) -> None:
        self.sender = sender

    def notify_started(self, run_id: int) -> None:
        self._send(f"🤖 Master AI run #{run_id} started.")

    def notify_approval_required(self, approval_id: int) -> None:
        self._send(f"⚠️ Master AI approval required: approval #{approval_id}.")

    def notify_failed(self, run_id: int, safe_error: str) -> None:
        self._send(f"🔴 Master AI run #{run_id} failed: {safe_error_message(safe_error) or 'unknown error'}")

    def notify_completed(self, run_id: int, summary: str) -> None:
        self._send(f"✅ Master AI run #{run_id} completed: {safe_error_message(summary) or 'done'}")

    def _send(self, message: str) -> None:
        try:
            if self.sender is not None:
                self.sender(message)
                return
            # Optional production integration.  The repository's Telegram service
            # has evolved across phases, so support common function names without
            # making notification delivery a hard dependency.
            try:
                from services import telegram_service
            except Exception:
                return
            for function_name in ("send_admin_message", "send_telegram_message", "send_message"):
                function = getattr(telegram_service, function_name, None)
                if callable(function):
                    function(message)
                    return
        except Exception:
            return
