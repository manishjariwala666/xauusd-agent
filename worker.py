"""Always-on Render worker for schedules and durable AI-agent jobs."""

from __future__ import annotations

import os
import socket
from threading import Event
from time import monotonic

from loguru import logger
from sqlalchemy import text

from config import get_settings
from core.database import session_scope
from services.job_queue import (
    claim_next_job,
    enqueue_due_schedules,
    finish_job,
    heartbeat,
)
from services.migration_service import apply_pending_migrations
from services.production_agents import RUNNERS


def run_worker(stop_event: Event | None = None) -> None:
    """Claim and execute jobs while isolating every failed execution."""
    event = stop_event or Event()
    settings = get_settings()
    worker_id = f"{socket.gethostname()}:{os.getpid()}"
    apply_pending_migrations()
    logger.info("AI worker started: {}", worker_id)
    while not event.is_set():
        try:
            heartbeat(worker_id)
            enqueue_due_schedules()
            job = claim_next_job(worker_id)
            if not job:
                event.wait(settings.worker_poll_seconds)
                continue
            run_id: int | None = None
            started = monotonic()
            try:
                run_id = _start_agent_run(
                    str(job["agent_key"]),
                    job.get("triggered_by"),
                )
                runner = RUNNERS[str(job["agent_key"])]
                result = runner(dict(job.get("payload") or {}))
            except Exception as exc:
                logger.exception(
                    "AI job failed: id={} agent={}",
                    job["id"],
                    job["agent_key"],
                )
                finish_job(int(job["id"]), False, str(exc))
                if run_id is not None:
                    _finish_agent_run(
                        run_id,
                        str(job["agent_key"]),
                        False,
                        int((monotonic() - started) * 1000),
                        None,
                        str(exc),
                    )
            else:
                logger.info(
                    "AI job completed: id={} result={}", job["id"], result
                )
                finish_job(int(job["id"]), True)
                _finish_agent_run(
                    run_id,
                    str(job["agent_key"]),
                    True,
                    int((monotonic() - started) * 1000),
                    result,
                    None,
                )
        except Exception:
            logger.exception("Worker iteration failed")
            event.wait(settings.worker_poll_seconds)


def _start_agent_run(agent_key: str, triggered_by: int | None) -> int:
    with session_scope() as session:
        agent_id = session.execute(
            text(
                """
                UPDATE public.ai_agents
                SET status = 'RUNNING', last_error = NULL, updated_at = NOW()
                WHERE agent_key = :key RETURNING id
                """
            ),
            {"key": agent_key},
        ).scalar_one()
        return int(
            session.execute(
                text(
                    """
                    INSERT INTO public.ai_agent_runs (
                        agent_id, status, triggered_by, trigger_type
                    ) VALUES (:agent_id, 'RUNNING', :triggered_by, 'SCHEDULED')
                    RETURNING id
                    """
                ),
                {"agent_id": agent_id, "triggered_by": triggered_by},
            ).scalar_one()
        )


def _finish_agent_run(
    run_id: int,
    agent_key: str,
    success: bool,
    duration_ms: int,
    result: str | None,
    error: str | None,
) -> None:
    with session_scope() as session:
        session.execute(
            text(
                """
                UPDATE public.ai_agent_runs
                SET status = :run_status, finished_at = NOW(),
                    duration_ms = :duration, result_summary = :result,
                    error_message = :error
                WHERE id = :run_id
                """
            ),
            {
                "run_status": "SUCCESS" if success else "ERROR",
                "duration": duration_ms,
                "result": result[:1000] if result else None,
                "error": error[:2000] if error else None,
                "run_id": run_id,
            },
        )
        session.execute(
            text(
                """
                UPDATE public.ai_agents
                SET status = :status, last_run_at = NOW(),
                    last_error = :error,
                    success_count = success_count + :success,
                    failure_count = failure_count + :failure,
                    updated_at = NOW()
                WHERE agent_key = :key
                """
            ),
            {
                "status": "IDLE" if success else "ERROR",
                "error": error[:2000] if error else None,
                "success": 1 if success else 0,
                "failure": 0 if success else 1,
                "key": agent_key,
            },
        )


if __name__ == "__main__":
    run_worker()
