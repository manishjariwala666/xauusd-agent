"""Master AI Orchestrator execution engine.

Phase P6.1 implements orchestration around existing worker agents.  Existing
manual/scheduled agent execution paths remain unchanged; this engine delegates
worker execution through ``WorkerAgentAdapter``.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any
import json
from uuid import uuid4

from services.agent_message_bus import AgentMessageBus
from services.execution_graph import ExecutionGraphNode, ExecutionGraphService, TERMINAL_STEP_STATUSES
from services.execution_planner import AgentDescriptor, ExecutionPlan, ExecutionPlanner
from services.orchestration_memory import OrchestrationMemoryService
from services.orchestration_notifications import OrchestrationNotificationService
from services.orchestration_redaction import redact_value, safe_error_message
from services.shared_task_context import SharedTaskContextService
from services.worker_agent_adapter import WorkerAgentAdapter, WorkerAgentResult

TERMINAL_RUN_STATUSES = {"COMPLETED", "PARTIAL_SUCCESS", "FAILED", "CANCELLED", "BLOCKED"}


@dataclass(frozen=True)
class OrchestrationRunRef:
    """Identifier returned by orchestration entrypoints."""

    run_id: int
    task_id: int
    status: str = "CREATED"


@dataclass(frozen=True)
class OrchestrationTaskRequest:
    """High-level task request accepted by the Master AI."""

    task_type: str
    title: str
    input_payload: dict[str, Any] = field(default_factory=dict)
    requested_by: int | None = None
    source: str = "ADMIN_DASHBOARD"


@dataclass(frozen=True)
class OrchestrationProgress:
    run_id: int
    task_id: int
    status: str
    completed_steps: int
    total_steps: int
    failed_steps: int = 0
    plan_summary: str | None = None
    final_summary: str | None = None
    safe_error: str | None = None


class MasterOrchestrator:
    """Coordinate high-level tasks across existing worker agents."""

    def __init__(
        self,
        *,
        planner: ExecutionPlanner | None = None,
        graph: ExecutionGraphService | None = None,
        context: SharedTaskContextService | None = None,
        memory: OrchestrationMemoryService | None = None,
        message_bus: AgentMessageBus | None = None,
        notifications: OrchestrationNotificationService | None = None,
        worker_adapter: WorkerAgentAdapter | None = None,
        max_parallel_workers: int = 4,
    ) -> None:
        self.planner = planner or ExecutionPlanner()
        self.graph = graph or ExecutionGraphService()
        self.context = context or SharedTaskContextService()
        self.memory = memory or OrchestrationMemoryService()
        self.message_bus = message_bus or AgentMessageBus()
        self.notifications = notifications or OrchestrationNotificationService()
        self.worker_adapter = worker_adapter or WorkerAgentAdapter()
        self.max_parallel_workers = max(1, min(int(max_parallel_workers), 8))

    def create_task(self, request: OrchestrationTaskRequest) -> OrchestrationRunRef:
        """Create a high-level task and initial orchestration run."""
        from sqlalchemy import text
        from core.database import session_scope

        task_key = f"master-{uuid4().hex}"
        safe_payload = redact_value(request.input_payload or {})
        risk_level = str((request.input_payload or {}).get("risk_level") or "LOW").upper()
        if risk_level not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
            risk_level = "LOW"

        with session_scope() as session:
            task_id = session.execute(
                text(
                    """
                    INSERT INTO public.master_ai_tasks (
                        task_key, task_type, title, description, source,
                        requested_by, risk_level, input_payload_redacted, status
                    ) VALUES (
                        :task_key, :task_type, :title, :description, :source,
                        :requested_by, :risk_level, CAST(:payload AS JSONB), 'CREATED'
                    ) RETURNING id
                    """
                ),
                {
                    "task_key": task_key,
                    "task_type": request.task_type,
                    "title": request.title,
                    "description": str((request.input_payload or {}).get("description") or ""),
                    "source": request.source,
                    "requested_by": request.requested_by,
                    "risk_level": risk_level,
                    "payload": json.dumps(safe_payload),
                },
            ).scalar_one()
            run_id = session.execute(
                text(
                    """
                    INSERT INTO public.master_ai_runs (task_id, status)
                    VALUES (:task_id, 'CREATED')
                    RETURNING id
                    """
                ),
                {"task_id": int(task_id)},
            ).scalar_one()

        self.context.initialize_context(orchestration_run_id=int(run_id), input_payload=safe_payload)
        self.memory.append_entry(
            orchestration_run_id=int(run_id),
            entry_type="TASK_RECEIVED",
            summary=f"Task received: {request.title}",
            data=safe_payload,
            created_by="MASTER_AI",
        )
        return OrchestrationRunRef(run_id=int(run_id), task_id=int(task_id), status="CREATED")

    def plan_task(self, *, orchestration_run_id: int) -> ExecutionPlan:
        """Create and persist an execution plan for a run."""
        task = self._load_task_for_run(orchestration_run_id)
        available_agents = self._load_available_agents()
        context = self.context.get_context_for_agent(
            orchestration_run_id=orchestration_run_id,
            agent_key="MASTER_AI",
            step_key="planning",
        )
        self._update_run_status(orchestration_run_id, "PLANNING")
        plan = self.planner.build_plan(task=task, available_agents=available_agents, context=context)
        validation = self.planner.validate_plan(plan=plan)
        if not validation.is_valid:
            safe_error = "; ".join(validation.errors)
            self._update_run_status(orchestration_run_id, "FAILED", safe_error=safe_error)
            self.memory.append_entry(
                orchestration_run_id=orchestration_run_id,
                entry_type="STEP_FAILED",
                summary=f"Plan validation failed: {safe_error}",
                data={"errors": validation.errors},
                created_by="MASTER_AI",
            )
            raise ValueError(safe_error)

        self.graph.create_graph(orchestration_run_id=orchestration_run_id, plan=plan)
        plan_summary = self._plan_summary(plan)
        next_status = "WAITING_APPROVAL" if plan.requires_human_approval else "PLAN_READY"
        self._update_run_status(orchestration_run_id, next_status, plan_summary=plan_summary)
        self.memory.append_entry(
            orchestration_run_id=orchestration_run_id,
            entry_type="PLAN_CREATED",
            summary=plan_summary,
            data={"steps": [step.agent_key for step in plan.steps], "warnings": validation.warnings},
            created_by="MASTER_AI",
        )
        if plan.requires_human_approval:
            approval_id = self._create_approval(
                orchestration_run_id=orchestration_run_id,
                reason=f"Plan risk level is {plan.risk_level} or approval was explicitly requested.",
            )
            self.notifications.notify_approval_required(approval_id)
        return plan

    def start_task(self, *, orchestration_run_id: int) -> OrchestrationProgress:
        """Start or continue execution for a planned orchestration run."""
        progress = get_orchestration_progress(orchestration_run_id)
        if progress is None:
            raise ValueError(f"Unknown orchestration run: {orchestration_run_id}")
        if progress.status == "CREATED":
            self.plan_task(orchestration_run_id=orchestration_run_id)
            progress = get_orchestration_progress(orchestration_run_id)
        if progress and progress.status == "WAITING_APPROVAL":
            return progress
        if progress and progress.status in TERMINAL_RUN_STATUSES:
            return progress

        self.notifications.notify_started(orchestration_run_id)
        self._update_run_status(orchestration_run_id, "RUNNING", started=True)
        self.memory.append_entry(
            orchestration_run_id=orchestration_run_id,
            entry_type="DECISION",
            summary="Master AI started worker-agent execution.",
            data={},
            created_by="MASTER_AI",
        )

        try:
            self._execute_until_blocked_or_complete(orchestration_run_id)
            final_progress = get_orchestration_progress(orchestration_run_id)
            status = self._final_run_status(final_progress)
            summary = self._final_summary(final_progress)
            self._update_run_status(orchestration_run_id, status, final_summary=summary, finished=True)
            self.memory.append_entry(
                orchestration_run_id=orchestration_run_id,
                entry_type="FINAL_SUMMARY",
                summary=summary,
                data={"status": status},
                created_by="MASTER_AI",
            )
            if status in {"COMPLETED", "PARTIAL_SUCCESS"}:
                self.notifications.notify_completed(orchestration_run_id, summary)
            else:
                self.notifications.notify_failed(orchestration_run_id, summary)
        except Exception as exc:
            safe_error = safe_error_message(exc) or "Master AI execution failed."
            self._update_run_status(orchestration_run_id, "FAILED", safe_error=safe_error, finished=True)
            self.memory.append_entry(
                orchestration_run_id=orchestration_run_id,
                entry_type="STEP_FAILED",
                summary=safe_error,
                data={},
                created_by="MASTER_AI",
            )
            self.notifications.notify_failed(orchestration_run_id, safe_error)
            raise
        return get_orchestration_progress(orchestration_run_id) or progress

    def resume_task(self, *, orchestration_run_id: int) -> OrchestrationProgress:
        """Resume a non-terminal orchestration run."""
        return self.start_task(orchestration_run_id=orchestration_run_id)

    def cancel_task(
        self,
        *,
        orchestration_run_id: int,
        reason: str,
        requested_by: int | None = None,
    ) -> None:
        safe_reason = safe_error_message(reason) or "Cancelled by administrator."
        self._update_run_status(orchestration_run_id, "CANCELLED", safe_error=safe_reason, finished=True)
        self.memory.append_entry(
            orchestration_run_id=orchestration_run_id,
            entry_type="DECISION",
            summary=f"Run cancelled: {safe_reason}",
            data={"requested_by": requested_by},
            created_by="MASTER_AI",
        )

    def _execute_until_blocked_or_complete(self, orchestration_run_id: int) -> None:
        while True:
            runnable_steps = self.graph.get_runnable_steps(orchestration_run_id=orchestration_run_id)
            if not runnable_steps:
                return
            parallel_steps = [step for step in runnable_steps if step.metadata.get("can_run_parallel")]
            if len(parallel_steps) > 1:
                self._execute_parallel(orchestration_run_id, parallel_steps)
            else:
                self._execute_step(orchestration_run_id, runnable_steps[0])

    def _execute_parallel(self, orchestration_run_id: int, steps: list[ExecutionGraphNode]) -> None:
        with ThreadPoolExecutor(max_workers=min(self.max_parallel_workers, len(steps))) as executor:
            futures = [executor.submit(self._execute_step, orchestration_run_id, step) for step in steps]
            for future in as_completed(futures):
                future.result()

    def _execute_step(self, orchestration_run_id: int, step: ExecutionGraphNode) -> None:
        step_id = int(step.metadata["id"])
        max_attempts = int(step.metadata.get("max_attempts") or 1)
        self.graph.mark_step_status(step_id=step_id, status="RUNNING")
        self.memory.append_entry(
            orchestration_run_id=orchestration_run_id,
            entry_type="STEP_STARTED",
            summary=f"Started {step.agent_key}",
            data={"step_key": step.step_key, "agent_key": step.agent_key},
            created_by="MASTER_AI",
        )
        context = self.context.get_context_for_agent(
            orchestration_run_id=orchestration_run_id,
            agent_key=step.agent_key,
            step_key=step.step_key,
        )
        result = self.worker_adapter.execute_step(
            agent_key=step.agent_key,
            trigger_type="MASTER_AI",
            triggered_by=None,
            payload=context,
            orchestration_run_id=orchestration_run_id,
            orchestration_step_id=step_id,
        )
        attempt_count = int(step.metadata.get("attempt_count") or 0) + 1
        if result.succeeded:
            self._record_step_success(orchestration_run_id, step, step_id, result)
            return
        if result.transient_failure and attempt_count < max_attempts:
            self.graph.mark_step_status(
                step_id=step_id,
                status="READY",
                result={"output_summary": f"Transient failure; retrying: {result.message}"},
                error=result.message,
            )
            self.memory.append_entry(
                orchestration_run_id=orchestration_run_id,
                entry_type="DECISION",
                summary=f"Retry scheduled for {step.agent_key}: {result.message}",
                data={"step_key": step.step_key, "attempt_count": attempt_count, "max_attempts": max_attempts},
                created_by="MASTER_AI",
            )
            return
        self.graph.mark_step_status(
            step_id=step_id,
            status="FAILED",
            result={"output_summary": result.output_summary or result.message, "data_redacted": result.data_redacted},
            error=result.message,
        )
        self.memory.append_entry(
            orchestration_run_id=orchestration_run_id,
            entry_type="STEP_FAILED",
            summary=f"{step.agent_key} failed: {result.message}",
            data=result.data_redacted,
            created_by="MASTER_AI",
        )

    def _record_step_success(
        self,
        orchestration_run_id: int,
        step: ExecutionGraphNode,
        step_id: int,
        result: WorkerAgentResult,
    ) -> None:
        self.graph.mark_step_status(
            step_id=step_id,
            status="COMPLETED",
            result={"output_summary": result.output_summary or result.message, "data_redacted": result.data_redacted},
        )
        self.context.merge_step_output(
            orchestration_run_id=orchestration_run_id,
            step_key=step.step_key,
            output={"summary": result.output_summary or result.message, "data": result.data_redacted},
        )
        self.message_bus.send_message(
            orchestration_run_id=orchestration_run_id,
            from_agent_key=step.agent_key,
            to_agent_key="MASTER_AI",
            message_type="STEP_OUTPUT",
            payload={"summary": result.output_summary or result.message, "step_key": step.step_key},
        )
        self.memory.append_entry(
            orchestration_run_id=orchestration_run_id,
            entry_type="STEP_COMPLETED",
            summary=f"{step.agent_key} completed: {result.output_summary or result.message}",
            data=result.data_redacted,
            created_by="MASTER_AI",
        )

    def _load_task_for_run(self, orchestration_run_id: int) -> OrchestrationTaskRequest:
        from sqlalchemy import text
        from core.database import session_scope

        with session_scope() as session:
            row = (
                session.execute(
                    text(
                        """
                        SELECT t.id, t.task_type, t.title, t.source, t.requested_by,
                               t.input_payload_redacted
                        FROM public.master_ai_runs r
                        JOIN public.master_ai_tasks t ON t.id = r.task_id
                        WHERE r.id = :run_id
                        """
                    ),
                    {"run_id": orchestration_run_id},
                )
                .mappings()
                .first()
            )
        if row is None:
            raise ValueError(f"Unknown orchestration run: {orchestration_run_id}")
        return OrchestrationTaskRequest(
            task_type=str(row["task_type"]),
            title=str(row["title"]),
            input_payload=dict(row.get("input_payload_redacted") or {}),
            requested_by=row.get("requested_by"),
            source=str(row.get("source") or "ADMIN_DASHBOARD"),
        )

    def _load_available_agents(self) -> list[AgentDescriptor]:
        from services.ai_agent_service import list_ai_agents

        return [
            AgentDescriptor(
                agent_key=str(agent["agent_key"]),
                display_name=str(agent.get("display_name") or agent["agent_key"]),
                is_enabled=bool(agent.get("is_enabled", True)),
                metadata=dict(agent),
            )
            for agent in list_ai_agents()
        ]

    def _update_run_status(
        self,
        orchestration_run_id: int,
        status: str,
        *,
        plan_summary: str | None = None,
        final_summary: str | None = None,
        safe_error: str | None = None,
        started: bool = False,
        finished: bool = False,
    ) -> None:
        from sqlalchemy import text
        from core.database import session_scope

        with session_scope() as session:
            session.execute(
                text(
                    """
                    UPDATE public.master_ai_runs
                    SET status = :status,
                        plan_summary = COALESCE(:plan_summary, plan_summary),
                        final_summary = COALESCE(:final_summary, final_summary),
                        safe_error = :safe_error,
                        started_at = CASE WHEN :started THEN COALESCE(started_at, NOW()) ELSE started_at END,
                        finished_at = CASE WHEN :finished THEN NOW() ELSE finished_at END,
                        duration_ms = CASE
                            WHEN :finished AND started_at IS NOT NULL
                            THEN CAST(EXTRACT(EPOCH FROM (NOW() - started_at)) * 1000 AS INTEGER)
                            ELSE duration_ms
                        END,
                        updated_at = NOW()
                    WHERE id = :run_id
                    """
                ),
                {
                    "run_id": orchestration_run_id,
                    "status": status,
                    "plan_summary": plan_summary,
                    "final_summary": final_summary,
                    "safe_error": safe_error_message(safe_error),
                    "started": started,
                    "finished": finished,
                },
            )
            session.execute(
                text(
                    """
                    UPDATE public.master_ai_tasks t
                    SET status = :status, updated_at = NOW()
                    FROM public.master_ai_runs r
                    WHERE r.task_id = t.id AND r.id = :run_id
                    """
                ),
                {"run_id": orchestration_run_id, "status": status},
            )

    def _create_approval(self, *, orchestration_run_id: int, reason: str) -> int:
        from sqlalchemy import text
        from core.database import session_scope

        with session_scope() as session:
            approval_id = session.execute(
                text(
                    """
                    INSERT INTO public.master_ai_approvals (
                        run_id, approval_type, reason
                    ) VALUES (
                        :run_id, 'PLAN_APPROVAL', :reason
                    ) RETURNING id
                    """
                ),
                {"run_id": orchestration_run_id, "reason": reason},
            ).scalar_one()
            return int(approval_id)

    @staticmethod
    def _plan_summary(plan: ExecutionPlan) -> str:
        agent_order = " → ".join(step.agent_key for step in plan.steps) or "no workers"
        return f"{len(plan.steps)} step(s), risk={plan.risk_level}, workers={agent_order}"

    @staticmethod
    def _final_summary(progress: OrchestrationProgress | None) -> str:
        if progress is None:
            return "Run finished but progress could not be loaded."
        return (
            f"{progress.completed_steps}/{progress.total_steps} steps completed; "
            f"{progress.failed_steps} failed."
        )

    @staticmethod
    def _final_run_status(progress: OrchestrationProgress | None) -> str:
        if progress is None or progress.total_steps == 0:
            return "FAILED"
        if progress.failed_steps == 0 and progress.completed_steps == progress.total_steps:
            return "COMPLETED"
        if progress.completed_steps > 0:
            return "PARTIAL_SUCCESS"
        return "FAILED"


def create_and_start_master_task(
    *,
    task_type: str,
    title: str,
    input_payload: dict[str, Any] | None = None,
    requested_by: int | None = None,
    source: str = "ADMIN_DASHBOARD",
    supabase: Any | None = None,
) -> OrchestrationProgress:
    """Dashboard-friendly helper to create, plan, and start a Master AI task."""
    orchestrator = MasterOrchestrator(worker_adapter=WorkerAgentAdapter(supabase=supabase))
    ref = orchestrator.create_task(
        OrchestrationTaskRequest(
            task_type=task_type,
            title=title,
            input_payload=input_payload or {},
            requested_by=requested_by,
            source=source,
        )
    )
    orchestrator.plan_task(orchestration_run_id=ref.run_id)
    return orchestrator.start_task(orchestration_run_id=ref.run_id)


def list_orchestration_runs(limit: int = 25) -> list[dict[str, Any]]:
    """Return safe orchestration run rows for dashboard display."""
    from sqlalchemy import text
    from core.database import session_scope

    with session_scope() as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT r.id AS run_id, r.task_id, t.title, t.task_type,
                           r.status, r.plan_summary, r.final_summary, r.safe_error,
                           r.started_at, r.finished_at, r.duration_ms,
                           COUNT(s.id) AS total_steps,
                           COUNT(s.id) FILTER (WHERE s.status = 'COMPLETED') AS completed_steps,
                           COUNT(s.id) FILTER (WHERE s.status = 'FAILED') AS failed_steps
                    FROM public.master_ai_runs r
                    JOIN public.master_ai_tasks t ON t.id = r.task_id
                    LEFT JOIN public.master_ai_execution_steps s ON s.run_id = r.id
                    GROUP BY r.id, r.task_id, t.title, t.task_type, r.status,
                             r.plan_summary, r.final_summary, r.safe_error,
                             r.started_at, r.finished_at, r.duration_ms
                    ORDER BY r.created_at DESC
                    LIMIT :limit
                    """
                ),
                {"limit": int(limit)},
            )
            .mappings()
            .all()
        )
    return [dict(row) for row in rows]


def get_orchestration_progress(orchestration_run_id: int) -> OrchestrationProgress | None:
    """Return aggregate progress for one orchestration run."""
    from sqlalchemy import text
    from core.database import session_scope

    with session_scope() as session:
        row = (
            session.execute(
                text(
                    """
                    SELECT r.id AS run_id, r.task_id, r.status, r.plan_summary,
                           r.final_summary, r.safe_error,
                           COUNT(s.id) AS total_steps,
                           COUNT(s.id) FILTER (WHERE s.status = 'COMPLETED') AS completed_steps,
                           COUNT(s.id) FILTER (WHERE s.status = 'FAILED') AS failed_steps
                    FROM public.master_ai_runs r
                    LEFT JOIN public.master_ai_execution_steps s ON s.run_id = r.id
                    WHERE r.id = :run_id
                    GROUP BY r.id, r.task_id, r.status, r.plan_summary,
                             r.final_summary, r.safe_error
                    """
                ),
                {"run_id": orchestration_run_id},
            )
            .mappings()
            .first()
        )
    if row is None:
        return None
    return OrchestrationProgress(
        run_id=int(row["run_id"]),
        task_id=int(row["task_id"]),
        status=str(row["status"]),
        completed_steps=int(row.get("completed_steps") or 0),
        total_steps=int(row.get("total_steps") or 0),
        failed_steps=int(row.get("failed_steps") or 0),
        plan_summary=row.get("plan_summary"),
        final_summary=row.get("final_summary"),
        safe_error=row.get("safe_error"),
    )
