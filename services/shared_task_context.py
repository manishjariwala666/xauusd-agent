"""Shared task context service interfaces for Phase P6.0.

No context persistence, merging, or redaction logic is implemented yet.
"""

from __future__ import annotations

from typing import Any


class SharedTaskContextService:
    """Future versioned shared-context API for orchestration steps."""

    def initialize_context(
        self,
        *,
        orchestration_run_id: int,
        input_payload: dict[str, Any],
    ) -> int:
        raise NotImplementedError("Shared context initialization is not implemented in P6.0.")

    def get_context_for_agent(
        self,
        *,
        orchestration_run_id: int,
        agent_key: str,
        step_key: str,
    ) -> dict[str, Any]:
        raise NotImplementedError("Agent context views are not implemented in P6.0.")

    def merge_step_output(
        self,
        *,
        orchestration_run_id: int,
        step_key: str,
        output: dict[str, Any],
    ) -> int:
        raise NotImplementedError("Shared context merging is not implemented in P6.0.")
