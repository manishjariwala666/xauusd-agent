"""Master AI Orchestrator service skeleton for Phase P6.0.

Phase P6.0 intentionally adds service interfaces only. No planning,
execution, dispatch, retry, approval, notification, or business logic is
implemented here yet. Existing agent behavior must remain unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class OrchestrationRunRef:
    """Identifier returned by future orchestration entrypoints."""

    run_id: int
    task_id: int
    status: str = "CREATED"


@dataclass(frozen=True)
class OrchestrationTaskRequest:
    """High-level task request accepted by the future Master AI."""

    task_type: str
    title: str
    input_payload: dict[str, Any] = field(default_factory=dict)
    requested_by: int | None = None
    source: str = "ADMIN_DASHBOARD"


class MasterOrchestrator:
    """Future coordinator for high-level Master AI tasks.

    This class is a Phase P6.0 interface placeholder. Methods raise
    ``NotImplementedError`` until Phase P6.1+ adds execution behavior.
    """

    def create_task(self, request: OrchestrationTaskRequest) -> OrchestrationRunRef:
        """Create an orchestration task in a later implementation phase."""
        raise NotImplementedError("Master AI task creation is not implemented in P6.0.")

    def plan_task(self, *, orchestration_run_id: int) -> Any:
        """Plan an orchestration task in a later implementation phase."""
        raise NotImplementedError("Master AI planning is not implemented in P6.0.")

    def start_task(self, *, orchestration_run_id: int) -> None:
        """Start an orchestration task in a later implementation phase."""
        raise NotImplementedError("Master AI execution is not implemented in P6.0.")

    def resume_task(self, *, orchestration_run_id: int) -> None:
        """Resume an orchestration task in a later implementation phase."""
        raise NotImplementedError("Master AI resume is not implemented in P6.0.")

    def cancel_task(
        self,
        *,
        orchestration_run_id: int,
        reason: str,
        requested_by: int | None = None,
    ) -> None:
        """Cancel an orchestration task in a later implementation phase."""
        raise NotImplementedError("Master AI cancellation is not implemented in P6.0.")
