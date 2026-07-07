"""Compatibility adapter for invoking existing worker agents.

The adapter preserves backward compatibility by delegating to the existing
``services.ai_agent_service.run_ai_agent`` entrypoint.  It does not rewrite or
replace worker agents.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from services.orchestration_redaction import redact_value, safe_error_message


@dataclass(frozen=True)
class WorkerAgentResult:
    succeeded: bool
    message: str
    output_summary: str | None = None
    data_redacted: dict[str, Any] = field(default_factory=dict)
    transient_failure: bool = False


class WorkerAgentAdapter:
    """Invoke existing agents from the orchestrator without changing them."""

    TRANSIENT_ERROR_MARKERS = (
        "timeout",
        "temporarily",
        "temporary",
        "rate limit",
        "too many requests",
        "connection",
        "network",
        "deadlock",
        "could not serialize",
        "try again",
    )

    def __init__(self, *, supabase: Any | None = None) -> None:
        self.supabase = supabase

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
        """Execute one worker agent through the existing compatibility path."""
        try:
            from services.ai_agent_service import run_ai_agent

            succeeded, message = run_ai_agent(
                agent_key=agent_key,
                triggered_by=triggered_by,
                supabase=self.supabase,
                payload=payload,
            )
        except Exception as exc:  # pragma: no cover - defensive runtime path
            safe_message = safe_error_message(exc) or "Worker agent execution failed."
            return WorkerAgentResult(
                succeeded=False,
                message=safe_message,
                output_summary=safe_message,
                data_redacted={
                    "agent_key": agent_key,
                    "trigger_type": trigger_type,
                    "orchestration_run_id": orchestration_run_id,
                    "orchestration_step_id": orchestration_step_id,
                },
                transient_failure=self._is_transient(safe_message),
            )

        safe_message = safe_error_message(message) or ""
        return WorkerAgentResult(
            succeeded=bool(succeeded),
            message=safe_message,
            output_summary=safe_message,
            data_redacted={
                "agent_key": agent_key,
                "trigger_type": trigger_type,
                "payload": redact_value(payload),
                "orchestration_run_id": orchestration_run_id,
                "orchestration_step_id": orchestration_step_id,
            },
            transient_failure=(not succeeded and self._is_transient(safe_message)),
        )

    def _is_transient(self, message: str) -> bool:
        lowered = message.lower()
        return any(marker in lowered for marker in self.TRANSIENT_ERROR_MARKERS)
