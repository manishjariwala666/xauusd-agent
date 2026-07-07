"""Execution planner interfaces for Phase P6.0.

No planning business logic is implemented in Phase P6.0.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AgentDescriptor:
    agent_key: str
    display_name: str
    is_enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionPlanStep:
    step_key: str
    agent_key: str
    title: str
    depends_on: tuple[str, ...] = ()
    can_run_parallel: bool = False
    approval_required: bool = False
    retry_policy: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionPlan:
    task_title: str
    objective: str
    risk_level: str = "LOW"
    requires_human_approval: bool = False
    steps: tuple[ExecutionPlanStep, ...] = ()


@dataclass(frozen=True)
class PlanValidationResult:
    is_valid: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


class ExecutionPlanner:
    """Future planner for transforming a task into a DAG plan."""

    def build_plan(
        self,
        *,
        task: Any,
        available_agents: list[AgentDescriptor],
        context: dict[str, Any],
    ) -> ExecutionPlan:
        """Build a plan in a later implementation phase."""
        raise NotImplementedError("Execution planning is not implemented in P6.0.")

    def validate_plan(self, *, plan: ExecutionPlan) -> PlanValidationResult:
        """Validate a plan in a later implementation phase."""
        raise NotImplementedError("Plan validation is not implemented in P6.0.")
