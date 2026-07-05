"""Durable PostgreSQL queue and schedule dispatcher for AI agents."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any

from sqlalchemy import text

from core.database import session_scope


def enqueue_agent_job(
    agent_key: str,
    payload: dict[str, Any] | None = None,
    triggered_by: int | None = None,
) -> int:
    """Create a durable queued run after validating the agent exists."""
    with session_scope() as session:
        job_id = session.execute(
            text(
                """
                INSERT INTO public.ai_agent_jobs (
                    agent_id, payload, triggered_by
                )
                SELECT id, CAST(:payload AS JSONB), :triggered_by
                FROM public.ai_agents
                WHERE agent_key = :agent_key AND is_enabled = TRUE
                RETURNING id
                """
            ),
            {
                "agent_key": agent_key,
                "payload": json.dumps(payload or {}),
                "triggered_by": triggered_by,
            },
        ).scalar_one_or_none()
    if job_id is None:
        raise ValueError("Agent is disabled or does not exist.")
    return int(job_id)


def enqueue_due_schedules() -> int:
    """Queue due schedules exactly once and advance their next run."""
    with session_scope() as session:
        rows = session.execute(
            text("SELECT * FROM public.enqueue_due_ai_agent_schedules()")
        ).all()
    return len(rows)


def claim_next_job(worker_id: str) -> dict[str, Any] | None:
    """Atomically claim one pending job using SKIP LOCKED."""
    with session_scope() as session:
        row = (
            session.execute(
                text(
                    """
                    WITH candidate AS (
                        SELECT j.id
                        FROM public.ai_agent_jobs j
                        JOIN public.ai_agents a ON a.id = j.agent_id
                        WHERE j.status = 'QUEUED'
                          AND j.available_at <= NOW()
                          AND a.is_enabled = TRUE
                        ORDER BY j.priority DESC, j.created_at
                        FOR UPDATE OF j SKIP LOCKED
                        LIMIT 1
                    )
                    UPDATE public.ai_agent_jobs j
                    SET status = 'RUNNING', worker_id = :worker_id,
                        started_at = NOW(), attempts = attempts + 1
                    FROM candidate
                    WHERE j.id = candidate.id
                    RETURNING j.id, j.payload, j.triggered_by,
                              (SELECT agent_key FROM public.ai_agents
                               WHERE id = j.agent_id) AS agent_key
                    """
                ),
                {"worker_id": worker_id},
            )
            .mappings()
            .first()
        )
    return dict(row) if row else None


def finish_job(job_id: int, success: bool, error: str | None = None) -> None:
    """Finalize a claimed job, retaining full operational history."""
    with session_scope() as session:
        session.execute(
            text(
                """
                UPDATE public.ai_agent_jobs
                SET status = :status, finished_at = NOW(),
                    last_error = :error
                WHERE id = :job_id
                """
            ),
            {
                "job_id": job_id,
                "status": "SUCCESS" if success else "ERROR",
                "error": error[:4000] if error else None,
            },
        )


def heartbeat(worker_id: str) -> None:
    """Upsert worker liveness without storing sensitive process data."""
    with session_scope() as session:
        session.execute(
            text(
                """
                INSERT INTO public.worker_heartbeats (worker_id, heartbeat_at)
                VALUES (:worker_id, :heartbeat_at)
                ON CONFLICT (worker_id) DO UPDATE
                SET heartbeat_at = EXCLUDED.heartbeat_at
                """
            ),
            {
                "worker_id": worker_id,
                "heartbeat_at": datetime.now(timezone.utc),
            },
        )
