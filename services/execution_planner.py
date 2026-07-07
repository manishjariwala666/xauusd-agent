"""Execution planner for the Master AI Orchestrator.

Phase P6.1 adds a deterministic, dependency-free planner.  It does not replace
or modify any existing worker agent.  It only decides which enabled worker
agents should be invoked and in what dependency order.
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
    """Rule-based planner for Phase P6.1 orchestration.

    The planner intentionally avoids LLM calls in P6.1 so the execution engine
    is deterministic, testable, and safe.  Future phases can swap in an AI
    planning strategy behind the same interface.
    """

    KEYWORD_AGENT_HINTS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
        (("telegram", "tg", "bot"), ("telegram",)),
        (("whatsapp", "wa", "reply", "conversation"), ("whatsapp", "reply")),
        (("blog", "article", "seo", "content", "post"), ("blog", "content")),
        (("image", "poster", "creative", "screenshot"), ("image", "content")),
        (("market", "signal", "xauusd", "gold", "price"), ("market", "signal")),
        (("email", "mail", "customer"), ("email",)),
    )

    def build_plan(
        self,
        *,
        task: Any,
        available_agents: list[AgentDescriptor],
        context: dict[str, Any],
    ) -> ExecutionPlan:
        """Build a safe execution plan from a high-level task.

        Supported explicit payload options:
        - ``agent_keys``: ordered list of worker agent keys to execute.
        - ``parallel``: when true, steps without dependencies can run together.
        - ``max_attempts``: retry attempts per step, clamped to 1..5.
        - ``requires_human_approval``: forces the plan into approval-required.
        """
        input_payload = dict(getattr(task, "input_payload", {}) or {})
        title = str(getattr(task, "title", "Master AI task") or "Master AI task")
        task_type = str(getattr(task, "task_type", "GENERAL") or "GENERAL")
        objective = str(input_payload.get("objective") or input_payload.get("description") or title)
        risk_level = str(input_payload.get("risk_level") or "LOW").upper()
        if risk_level not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
            risk_level = "LOW"

        enabled_agents = [agent for agent in available_agents if agent.is_enabled]
        selected_keys = self._select_agent_keys(
            task_type=task_type,
            title=title,
            payload=input_payload,
            enabled_agents=enabled_agents,
        )

        parallel = bool(input_payload.get("parallel", False))
        max_attempts = self._max_attempts(input_payload.get("max_attempts", 2))
        requires_approval = bool(input_payload.get("requires_human_approval", False)) or risk_level in {
            "HIGH",
            "CRITICAL",
        }

        steps: list[ExecutionPlanStep] = []
        previous_step_key: str | None = None
        for index, agent_key in enumerate(selected_keys, start=1):
            step_key = f"step_{index}_{self._safe_step_key(agent_key)}"
            depends_on = () if parallel or previous_step_key is None else (previous_step_key,)
            steps.append(
                ExecutionPlanStep(
                    step_key=step_key,
                    agent_key=agent_key,
                    title=f"Run {agent_key}",
                    depends_on=depends_on,
                    can_run_parallel=parallel and not depends_on,
                    approval_required=requires_approval,
                    retry_policy={
                        "max_attempts": max_attempts,
                        "retry_transient_failures": True,
                        "backoff_seconds": [0, 2, 5, 10][:max_attempts],
                    },
                )
            )
            previous_step_key = step_key

        return ExecutionPlan(
            task_title=title,
            objective=objective,
            risk_level=risk_level,
            requires_human_approval=requires_approval,
            steps=tuple(steps),
        )

    def validate_plan(self, *, plan: ExecutionPlan) -> PlanValidationResult:
        """Validate dependency shape and required step fields."""
        errors: list[str] = []
        warnings: list[str] = []
        if not plan.steps:
            errors.append("Plan has no executable worker-agent steps.")

        seen: set[str] = set()
        for step in plan.steps:
            if not step.step_key:
                errors.append("Plan contains a step without step_key.")
            if not step.agent_key:
                errors.append(f"Step {step.step_key or '<unknown>'} has no agent_key.")
            if step.step_key in seen:
                errors.append(f"Duplicate step_key: {step.step_key}.")
            seen.add(step.step_key)

        for step in plan.steps:
            for dependency in step.depends_on:
                if dependency not in seen:
                    errors.append(f"Step {step.step_key} depends on missing step {dependency}.")
                if dependency == step.step_key:
                    errors.append(f"Step {step.step_key} cannot depend on itself.")

        if plan.requires_human_approval:
            warnings.append("Human approval required before execution.")

        return PlanValidationResult(
            is_valid=not errors,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    def _select_agent_keys(
        self,
        *,
        task_type: str,
        title: str,
        payload: dict[str, Any],
        enabled_agents: list[AgentDescriptor],
    ) -> list[str]:
        available_by_key = {agent.agent_key: agent for agent in enabled_agents}
        explicit_keys = payload.get("agent_keys") or payload.get("agents")
        if isinstance(explicit_keys, str):
            explicit_keys = [explicit_keys]
        if isinstance(explicit_keys, list):
            selected = [str(key) for key in explicit_keys if str(key) in available_by_key]
            if selected:
                return selected

        haystack = " ".join(
            str(value)
            for value in (task_type, title, payload.get("objective"), payload.get("description"))
            if value is not None
        ).lower()
        selected: list[str] = []
        for keywords, key_hints in self.KEYWORD_AGENT_HINTS:
            if not any(keyword in haystack for keyword in keywords):
                continue
            for agent in enabled_agents:
                agent_key = agent.agent_key.lower()
                display_name = agent.display_name.lower()
                if any(hint in agent_key or hint in display_name for hint in key_hints):
                    selected.append(agent.agent_key)

        deduped = list(dict.fromkeys(selected))
        if deduped:
            return deduped
        return [enabled_agents[0].agent_key] if enabled_agents else []

    @staticmethod
    def _safe_step_key(agent_key: str) -> str:
        return "".join(char if char.isalnum() else "_" for char in agent_key.lower()).strip("_") or "agent"

    @staticmethod
    def _max_attempts(value: Any) -> int:
        try:
            attempts = int(value)
        except (TypeError, ValueError):
            attempts = 2
        return max(1, min(attempts, 5))
