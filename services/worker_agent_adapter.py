"""Compatibility adapter for invoking existing worker agents.

Historical scheduled workers remain delegated through ``run_ai_agent`` so their
shared DB enabled/disabled state and run history stay authoritative. A small,
explicit allowlist of safe Master-AI-only agents can execute directly through
their existing production runner because those agents were added after the
historical ``ai_agents`` seed and are not scheduler workers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from services.orchestration_redaction import redact_value, safe_error_message


ORCHESTRATION_NATIVE_AGENT_KEYS = frozenset(
    {
        "market_data_agent",
        "customer_support_agent",
        "marketing_strategy_agent",
        "social_media_agent",
        "cms_editor_agent",
        "master_content_review_agent",
    }
)


@dataclass(frozen=True)
class WorkerAgentResult:
    succeeded: bool
    message: str
    output_summary: str | None = None
    data_redacted: dict[str, Any] = field(default_factory=dict)
    transient_failure: bool = False


class WorkerAgentAdapter:
    """Invoke exact registered agents without substituting workers."""

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
        """Execute one exact agent through its approved compatibility path."""
        clean_key = str(agent_key or "").strip()
        clean_trigger = str(trigger_type or "").strip().upper()
        try:
            if (
                clean_trigger == "MASTER_AI"
                and clean_key in ORCHESTRATION_NATIVE_AGENT_KEYS
            ):
                succeeded, message = self._run_orchestration_native(
                    clean_key,
                    payload,
                )
            else:
                from services.ai_agent_service import run_ai_agent

                succeeded, message = run_ai_agent(
                    agent_key=clean_key,
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
                    "agent_key": clean_key,
                    "trigger_type": clean_trigger,
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
                "agent_key": clean_key,
                "trigger_type": clean_trigger,
                "payload": redact_value(payload),
                "orchestration_run_id": orchestration_run_id,
                "orchestration_step_id": orchestration_step_id,
            },
            transient_failure=(not succeeded and self._is_transient(safe_message)),
        )

    @staticmethod
    def _run_orchestration_native(
        agent_key: str,
        payload: dict[str, Any],
    ) -> tuple[bool, str]:
        """Run only the fixed safe Master-AI-native allowlist."""
        if agent_key not in ORCHESTRATION_NATIVE_AGENT_KEYS:
            return False, "Agent is not approved for native Master AI execution."

        from services.production_agents import RUNNERS

        runner = RUNNERS.get(agent_key)
        if runner is None:
            return False, f"Exact agent '{agent_key}' has no production runner configured."
        result = runner(payload or {})
        if not isinstance(result, str) or not result.strip():
            return False, "Production runner returned no verifiable result."
        return True, result.strip()

    def _is_transient(self, message: str) -> bool:
        lowered = message.lower()
        return any(marker in lowered for marker in self.TRANSIENT_ERROR_MARKERS)
