"""Telegram/admin notification interfaces for Phase P6.0.

No notifications are sent in Phase P6.0.
"""

from __future__ import annotations


class OrchestrationNotificationService:
    """Future notification facade for Master AI lifecycle events."""

    def notify_started(self, run_id: int) -> None:
        raise NotImplementedError("Orchestration notifications are not implemented in P6.0.")

    def notify_approval_required(self, approval_id: int) -> None:
        raise NotImplementedError("Orchestration notifications are not implemented in P6.0.")

    def notify_failed(self, run_id: int, safe_error: str) -> None:
        raise NotImplementedError("Orchestration notifications are not implemented in P6.0.")

    def notify_completed(self, run_id: int, summary: str) -> None:
        raise NotImplementedError("Orchestration notifications are not implemented in P6.0.")
