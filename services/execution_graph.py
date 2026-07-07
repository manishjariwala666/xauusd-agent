"""Execution graph service interfaces for Phase P6.0.

No graph creation or state-transition logic is implemented in Phase P6.0.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ExecutionGraphNode:
    step_key: str
    agent_key: str
    status: str = "PENDING"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionGraphEdge:
    from_step_key: str
    to_step_key: str
    edge_type: str = "DEPENDS_ON"
    condition: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionGraph:
    run_id: int
    nodes: tuple[ExecutionGraphNode, ...] = ()
    edges: tuple[ExecutionGraphEdge, ...] = ()


class ExecutionGraphService:
    """Future DAG service for orchestration step dependencies."""

    def create_graph(self, *, orchestration_run_id: int, plan: Any) -> ExecutionGraph:
        raise NotImplementedError("Execution graph creation is not implemented in P6.0.")

    def get_runnable_steps(self, *, orchestration_run_id: int) -> list[ExecutionGraphNode]:
        raise NotImplementedError("Runnable-step selection is not implemented in P6.0.")

    def mark_step_status(
        self,
        *,
        step_id: int,
        status: str,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        raise NotImplementedError("Step status updates are not implemented in P6.0.")
