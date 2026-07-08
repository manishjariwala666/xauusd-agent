"""Execution graph service for Master AI orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import json

from services.orchestration_redaction import redact_value, safe_error_message

TERMINAL_STEP_STATUSES = {"COMPLETED", "FAILED", "SKIPPED", "CANCELLED", "BLOCKED"}
SUCCESS_STEP_STATUSES = {"COMPLETED", "SKIPPED"}


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
    """Persist and update orchestration DAG state."""

    def create_graph(self, *, orchestration_run_id: int, plan: Any) -> ExecutionGraph:
        from sqlalchemy import text
        from core.database import session_scope

        nodes: list[ExecutionGraphNode] = []
        edges: list[ExecutionGraphEdge] = []
        step_ids_by_key: dict[str, int] = {}
        with session_scope() as session:
            for step in plan.steps:
                status = "WAITING_APPROVAL" if step.approval_required else ("READY" if not step.depends_on else "PENDING")
                step_id = session.execute(
                    text(
                        """
                        INSERT INTO public.master_ai_execution_steps (
                            run_id, step_key, agent_id, agent_key, title, status,
                            can_run_parallel, approval_required, retry_policy,
                            max_attempts, input_payload_redacted
                        ) VALUES (
                            :run_id, :step_key,
                            (SELECT id FROM public.ai_agents WHERE agent_key = :agent_key LIMIT 1),
                            :agent_key, :title, :status,
                            :can_run_parallel, :approval_required,
                            CAST(:retry_policy AS JSONB), :max_attempts,
                            '{}'::jsonb
                        )
                        ON CONFLICT (run_id, step_key) DO UPDATE
                        SET agent_key = EXCLUDED.agent_key,
                            title = EXCLUDED.title,
                            can_run_parallel = EXCLUDED.can_run_parallel,
                            approval_required = EXCLUDED.approval_required,
                            retry_policy = EXCLUDED.retry_policy,
                            max_attempts = EXCLUDED.max_attempts,
                            updated_at = NOW()
                        RETURNING id
                        """
                    ),
                    {
                        "run_id": orchestration_run_id,
                        "step_key": step.step_key,
                        "agent_key": step.agent_key,
                        "title": step.title,
                        "status": status,
                        "can_run_parallel": bool(step.can_run_parallel),
                        "approval_required": bool(step.approval_required),
                        "retry_policy": json.dumps(redact_value(step.retry_policy)),
                        "max_attempts": int(step.retry_policy.get("max_attempts", 1)),
                    },
                ).scalar_one()
                step_ids_by_key[step.step_key] = int(step_id)
                nodes.append(
                    ExecutionGraphNode(
                        step_key=step.step_key,
                        agent_key=step.agent_key,
                        status=status,
                        metadata={"id": int(step_id), "max_attempts": int(step.retry_policy.get("max_attempts", 1))},
                    )
                )

            for step in plan.steps:
                for dependency in step.depends_on:
                    from_id = step_ids_by_key[dependency]
                    to_id = step_ids_by_key[step.step_key]
                    session.execute(
                        text(
                            """
                            INSERT INTO public.master_ai_execution_edges (
                                run_id, from_step_id, to_step_id, edge_type, condition
                            ) VALUES (
                                :run_id, :from_step_id, :to_step_id, 'DEPENDS_ON', '{}'::jsonb
                            ) ON CONFLICT (from_step_id, to_step_id) DO NOTHING
                            """
                        ),
                        {"run_id": orchestration_run_id, "from_step_id": from_id, "to_step_id": to_id},
                    )
                    edges.append(ExecutionGraphEdge(from_step_key=dependency, to_step_key=step.step_key))

        return ExecutionGraph(run_id=orchestration_run_id, nodes=tuple(nodes), edges=tuple(edges))

    def get_runnable_steps(self, *, orchestration_run_id: int) -> list[ExecutionGraphNode]:
        from sqlalchemy import text
        from core.database import session_scope

        with session_scope() as session:
            rows = (
                session.execute(
                    text(
                        """
                        SELECT s.id, s.step_key, s.agent_key, s.status, s.attempt_count,
                               s.max_attempts, s.retry_policy, s.can_run_parallel
                        FROM public.master_ai_execution_steps s
                        WHERE s.run_id = :run_id
                          AND s.status IN ('READY', 'PENDING')
                          AND NOT EXISTS (
                              SELECT 1
                              FROM public.master_ai_execution_edges e
                              JOIN public.master_ai_execution_steps parent
                                ON parent.id = e.from_step_id
                              WHERE e.to_step_id = s.id
                                AND parent.status NOT IN ('COMPLETED', 'SKIPPED')
                          )
                        ORDER BY s.created_at ASC, s.id ASC
                        """
                    ),
                    {"run_id": orchestration_run_id},
                )
                .mappings()
                .all()
            )
        return [
            ExecutionGraphNode(
                step_key=str(row["step_key"]),
                agent_key=str(row["agent_key"]),
                status=str(row["status"]),
                metadata={
                    "id": int(row["id"]),
                    "attempt_count": int(row.get("attempt_count") or 0),
                    "max_attempts": int(row.get("max_attempts") or 1),
                    "retry_policy": dict(row.get("retry_policy") or {}),
                    "can_run_parallel": bool(row.get("can_run_parallel")),
                },
            )
            for row in rows
        ]

    def list_steps(self, *, orchestration_run_id: int) -> list[ExecutionGraphNode]:
        from sqlalchemy import text
        from core.database import session_scope

        with session_scope() as session:
            rows = (
                session.execute(
                    text(
                        """
                        SELECT id, step_key, agent_key, status, attempt_count,
                               max_attempts, retry_policy, output_summary, safe_error
                        FROM public.master_ai_execution_steps
                        WHERE run_id = :run_id
                        ORDER BY created_at ASC, id ASC
                        """
                    ),
                    {"run_id": orchestration_run_id},
                )
                .mappings()
                .all()
            )
        return [
            ExecutionGraphNode(
                step_key=str(row["step_key"]),
                agent_key=str(row["agent_key"]),
                status=str(row["status"]),
                metadata={
                    "id": int(row["id"]),
                    "attempt_count": int(row.get("attempt_count") or 0),
                    "max_attempts": int(row.get("max_attempts") or 1),
                    "retry_policy": dict(row.get("retry_policy") or {}),
                    "output_summary": row.get("output_summary"),
                    "safe_error": row.get("safe_error"),
                },
            )
            for row in rows
        ]

    def mark_step_status(
        self,
        *,
        step_id: int,
        status: str,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        from sqlalchemy import text
        from core.database import session_scope

        safe_error = safe_error_message(error)
        result = result or {}
        with session_scope() as session:
            session.execute(
                text(
                    """
                    UPDATE public.master_ai_execution_steps
                    SET status = :status,
                        attempt_count = CASE WHEN :status = 'RUNNING'
                            THEN attempt_count + 1 ELSE attempt_count END,
                        output_summary = COALESCE(CAST(:output_summary AS TEXT), output_summary),
                        output_payload_redacted = COALESCE(
                            CAST(:output_payload_redacted AS JSONB),
                            output_payload_redacted
                        ),
                        records_processed = COALESCE(CAST(:records_processed AS INTEGER), records_processed),
                        db_tables_written = COALESCE(CAST(:db_tables_written AS TEXT[]), db_tables_written),
                        external_services_called = COALESCE(CAST(:external_services_called AS TEXT[]), external_services_called),
                        generated_files = CASE WHEN :generated_files IS NULL
                            THEN generated_files ELSE CAST(:generated_files AS JSONB) END,
                        setup_warnings = COALESCE(CAST(:setup_warnings AS TEXT[]), setup_warnings),
                        safe_error = :safe_error,
                        started_at = CASE WHEN :status = 'RUNNING' THEN COALESCE(started_at, NOW()) ELSE started_at END,
                        finished_at = CASE WHEN :status IN ('COMPLETED', 'FAILED', 'SKIPPED', 'CANCELLED', 'BLOCKED') THEN NOW() ELSE finished_at END,
                        duration_ms = CASE
                            WHEN :status IN ('COMPLETED', 'FAILED', 'SKIPPED', 'CANCELLED', 'BLOCKED') AND started_at IS NOT NULL
                            THEN CAST(EXTRACT(EPOCH FROM (NOW() - started_at)) * 1000 AS INTEGER)
                            ELSE duration_ms
                        END,
                        updated_at = NOW()
                    WHERE id = :step_id
                    """
                ),
                {
                    "step_id": step_id,
                    "status": status,
                    "output_summary": result.get("output_summary"),
                    "output_payload_redacted": json.dumps(redact_value(result.get("output_payload") or result.get("data_redacted"))) if result else None,
                    "records_processed": result.get("records_processed"),
                    "db_tables_written": result.get("db_tables_written"),
                    "external_services_called": result.get("external_services_called"),
                    "generated_files": json.dumps(redact_value(result.get("generated_files"))) if result.get("generated_files") is not None else None,
                    "setup_warnings": result.get("setup_warnings"),
                    "safe_error": safe_error,
                },
            )
