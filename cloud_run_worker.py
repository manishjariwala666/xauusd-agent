"""One-shot durable worker for Cloud Run Jobs.

Cloud Scheduler should execute this job every minute. Each invocation enqueues
any due AI-agent schedules, drains a bounded number of durable jobs, records
normal run history, then exits cleanly.
"""

from __future__ import annotations

import os
import socket
from time import monotonic

from loguru import logger

from services.job_queue import (
    claim_next_job,
    enqueue_due_schedules,
    finish_job,
    heartbeat,
)
from services.production_agents import RUNNERS
from worker import (
    _apply_startup_migrations,
    _finish_agent_run,
    _start_agent_run,
)


def _max_jobs() -> int:
    raw = str(os.getenv("CLOUD_RUN_WORKER_MAX_JOBS", "20")).strip()
    try:
        return max(1, min(100, int(raw)))
    except ValueError:
        return 20


def run_once() -> tuple[int, int]:
    """Enqueue due schedules and process a bounded queue batch."""
    worker_id = f"cloud-run-job:{socket.gethostname()}:{os.getpid()}"
    _apply_startup_migrations()
    heartbeat(worker_id)

    enqueued = enqueue_due_schedules()
    processed = 0
    failed = 0

    for _ in range(_max_jobs()):
        job = claim_next_job(worker_id)
        if not job:
            break

        processed += 1
        run_id: int | None = None
        started = monotonic()
        agent_key = str(job["agent_key"])

        try:
            run_id = _start_agent_run(
                agent_key,
                job.get("triggered_by"),
            )
            runner = RUNNERS[agent_key]
            result = runner(dict(job.get("payload") or {}))
        except Exception as exc:
            failed += 1
            logger.exception(
                "Cloud Run AI job failed: id={} agent={}",
                job["id"],
                agent_key,
            )
            finish_job(int(job["id"]), False, str(exc))
            if run_id is not None:
                _finish_agent_run(
                    run_id,
                    agent_key,
                    False,
                    int((monotonic() - started) * 1000),
                    None,
                    str(exc),
                )
        else:
            logger.info(
                "Cloud Run AI job completed: id={} result={}",
                job["id"],
                result,
            )
            finish_job(int(job["id"]), True)
            if run_id is not None:
                _finish_agent_run(
                    run_id,
                    agent_key,
                    True,
                    int((monotonic() - started) * 1000),
                    result,
                    None,
                )

    logger.info(
        "Cloud Run worker cycle complete: enqueued={} processed={} failed={}",
        enqueued,
        processed,
        failed,
    )
    return processed, failed


if __name__ == "__main__":
    _, failures = run_once()
    if failures:
        raise SystemExit(1)
