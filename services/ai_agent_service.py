"""Admin-only AI-agent state, audit history, and manual execution."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from loguru import logger
from sqlalchemy import text

from core.database import session_scope
from services.production_agents import RUNNERS


_MAX_ERROR_LENGTH = 2_000


def list_ai_agents() -> list[dict[str, Any]]:
    """Return agent status records in their configured display order."""
    with session_scope() as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT a.agent_key, a.display_name, a.is_enabled,
                           a.status, a.last_run_at, a.last_error,
                           a.schedule_minutes,
                           s.next_run_at AS next_scheduled_run_at,
                           a.success_count, a.failure_count,
                           COUNT(j.id) FILTER (
                               WHERE j.status = 'QUEUED'
                           ) AS queue_size,
                           MAX(r.duration_ms) AS last_duration_ms
                    FROM public.ai_agents a
                    LEFT JOIN public.ai_agent_schedules s
                      ON s.agent_id = a.id
                    LEFT JOIN public.ai_agent_jobs j ON j.agent_id = a.id
                    LEFT JOIN LATERAL (
                        SELECT duration_ms
                        FROM public.ai_agent_runs ar
                        WHERE ar.agent_id = a.id
                        ORDER BY ar.started_at DESC LIMIT 1
                    ) r ON TRUE
                    GROUP BY a.id, s.next_run_at
                    ORDER BY a.display_order, a.display_name
                    """
                )
            )
            .mappings()
            .all()
        )
    return [dict(row) for row in rows]


def set_ai_agent_enabled(agent_key: str, enabled: bool) -> None:
    """Enable or disable one configured agent."""
    with session_scope() as session:
        result = session.execute(
            text(
                """
                UPDATE public.ai_agents
                SET is_enabled = :enabled,
                    updated_at = NOW()
                WHERE agent_key = :agent_key
                """
            ),
            {"agent_key": agent_key, "enabled": enabled},
        )
        if result.rowcount != 1:
            raise ValueError(f"Unknown AI agent: {agent_key}")


def run_ai_agent(
    agent_key: str,
    triggered_by: int,
    supabase: Any,
    payload: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    """Run one enabled agent and persist its complete execution state."""
    run_id = _start_run(agent_key, triggered_by)
    if run_id is None:
        return False, "Agent is disabled, unavailable, or already running."

    started_at = datetime.now(timezone.utc)
    try:
        runner = RUNNERS.get(agent_key)
        if runner is None:
            raise RuntimeError("Production runner is not configured.")
        result_message = runner(payload or {})
    except Exception as exc:
        error = str(exc).strip() or exc.__class__.__name__
        logger.exception("Manual AI agent run failed: {}", agent_key)
        _finish_run(
            run_id,
            agent_key,
            succeeded=False,
            error=error,
            result=None,
            started_at=started_at,
        )
        return False, error

    _finish_run(
        run_id,
        agent_key,
        succeeded=True,
        error=None,
        result=result_message,
        started_at=started_at,
    )
    return True, result_message


def _start_run(agent_key: str, triggered_by: int) -> int | None:
    """Atomically mark an enabled, idle agent as running."""
    with session_scope() as session:
        agent = (
            session.execute(
                text(
                    """
                    UPDATE public.ai_agents
                    SET status = 'RUNNING',
                        last_error = NULL,
                        updated_at = NOW()
                    WHERE agent_key = :agent_key
                      AND is_enabled = TRUE
                      AND status <> 'RUNNING'
                    RETURNING id
                    """
                ),
                {"agent_key": agent_key},
            )
            .mappings()
            .first()
        )
        if not agent:
            return None
        run_id = session.execute(
            text(
                """
                INSERT INTO public.ai_agent_runs (
                    agent_id, status, triggered_by
                )
                VALUES (:agent_id, 'RUNNING', :triggered_by)
                RETURNING id
                """
            ),
            {
                "agent_id": agent["id"],
                "triggered_by": triggered_by,
            },
        ).scalar_one()
    return int(run_id)


def _finish_run(
    run_id: int,
    agent_key: str,
    succeeded: bool,
    error: str | None,
    result: str | None,
    started_at: datetime,
) -> None:
    """Finalize the run audit row and current agent status."""
    safe_error = error[:_MAX_ERROR_LENGTH] if error else None
    agent_status = "IDLE" if succeeded else "ERROR"
    run_status = "SUCCESS" if succeeded else "ERROR"
    duration_ms = int(
        (datetime.now(timezone.utc) - started_at).total_seconds() * 1000
    )
    with session_scope() as session:
        session.execute(
            text(
                """
                UPDATE public.ai_agent_runs
                SET status = :run_status,
                    finished_at = NOW(),
                    error_message = :error,
                    duration_ms = :duration_ms,
                    result_summary = :result
                WHERE id = :run_id
                """
            ),
            {
                "run_status": run_status,
                "error": safe_error,
                "run_id": run_id,
                "duration_ms": duration_ms,
                "result": result[:1000] if result else None,
            },
        )
        session.execute(
            text(
                """
                UPDATE public.ai_agents
                SET status = :agent_status,
                    last_run_at = NOW(),
                    last_error = :error,
                    success_count = success_count + :success_increment,
                    failure_count = failure_count + :failure_increment,
                    updated_at = NOW()
                WHERE agent_key = :agent_key
                """
            ),
            {
                "agent_status": agent_status,
                "error": safe_error,
                "agent_key": agent_key,
                "success_increment": 1 if succeeded else 0,
                "failure_increment": 0 if succeeded else 1,
            },
        )


def list_agent_runs(limit: int = 100) -> list[dict[str, Any]]:
    """Return execution history without prompts, payloads, or secrets."""
    with session_scope() as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT r.id, a.agent_key, a.display_name, r.status, r.trigger_type,
                           r.started_at, r.finished_at, r.duration_ms,
                           r.result_summary, r.error_message
                    FROM public.ai_agent_runs r
                    JOIN public.ai_agents a ON a.id = r.agent_id
                    ORDER BY r.started_at DESC LIMIT :limit
                    """
                ),
                {"limit": limit},
            )
            .mappings()
            .all()
        )
    return [dict(row) for row in rows]
