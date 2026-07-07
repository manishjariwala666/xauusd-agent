"""Compatibility adapter skeleton for existing worker agents in Phase P6.0.

Existing ``run_ai_agent`` behavior is not changed here. Future phases may use
this adapter to attach optional orchestration identifiers to worker-agent runs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class WorkerAgentResult:
    succeeded: bool
    message: str
    output_summary: str | None = None
    data_redacted: dict[str, Any] = field(default_factory=dict)


class WorkerAgentAdapter:
    """Future adapter for invoking existing agents from the orchestrator."""

    def execute_step(
        self,
        *,
        agent_key: str,
        trigger_type: str,
        triggered_by: int | None,
        payload: dict[str, Any],
        orchestration_run_id: int | None = None,
        orchestration_step_id: int | None = None,
    ) -> WorkerAgentResult:
        raise NotImplementedError("Worker-agent orchestration adapter is not implemented in P6.0.")
