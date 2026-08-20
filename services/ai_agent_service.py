"""Shared AI-agent registry state, audit history, and execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from typing import Any

from loguru import logger
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from core.database import session_scope
from services.production_agents import RUNNERS


_MAX_ERROR_LENGTH = 2_000

AI_AGENT_CONTROL_NUMBERS: tuple[tuple[int, str, str], ...] = (
    (1, "ai_blog_agent", "AI Blog Agent"),
    (2, "signal_agent", "Signal Agent"),
    (3, "telegram_reply_agent", "Telegram Reply Agent"),
    (4, "whatsapp_reply_agent", "WhatsApp Reply Agent"),
    (5, "announcement_agent", "Announcement Agent"),
    (6, "seo_agent", "SEO Agent"),
    (7, "image_agent", "Image Agent"),
)


@dataclass(frozen=True)
class AgentStartResult:
    run_id: int | None
    reason: str | None = None


@dataclass(frozen=True)
class StaleAgentRecoveryResult:
    agent_key: str
    recovered: bool
    run_id: int | None
    previous_enabled: bool | None
    status: str
    reason: str


def list_ai_agents() -> list[dict[str, Any]]:
    """Return the canonical shared registry used by Admin and Telegram."""
    try:
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
                               COUNT(j.id) FILTER (WHERE j.status = 'QUEUED') AS queue_size,
                               MAX(r.duration_ms) AS last_duration_ms
                        FROM public.ai_agents a
                        LEFT JOIN public.ai_agent_schedules s ON s.agent_id = a.id
                        LEFT JOIN public.ai_agent_jobs j ON j.agent_id = a.id
                        LEFT JOIN LATERAL (
                            SELECT duration_ms
                            FROM public.ai_agent_runs ar
                            WHERE ar.agent_id = a.id
                            ORDER BY ar.started_at DESC
                            LIMIT 1
                        ) r ON TRUE
                        GROUP BY a.id, s.next_run_at
                        ORDER BY a.display_order, a.display_name
                        """
                    )
                )
                .mappings()
                .all()
            )
    except ProgrammingError as exc:
        original = getattr(exc, "orig", None)
        sqlstate = getattr(original, "sqlstate", None)
        if sqlstate == "42P01":
            logger.warning(
                "AI-agent runtime tables are unavailable; returning read-only registry fallback."
            )
            return []
        raise

    result: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        key = str(item.get("agent_key") or "")
        runner_configured = key in RUNNERS
        enabled = bool(item.get("is_enabled"))
        status = str(item.get("status") or "UNKNOWN").upper()
        item["runner_configured"] = runner_configured
        item["executable"] = enabled and runner_configured and status != "RUNNING"
        if not runner_configured:
            item["execution_block_reason"] = "Production runner is not configured."
        elif not enabled:
            item["execution_block_reason"] = "Agent is disabled in the shared registry."
        elif status == "RUNNING":
            item["execution_block_reason"] = "Agent is already running."
        else:
            item["execution_block_reason"] = None
        result.append(item)
    return result


def set_ai_agent_enabled(agent_key: str, enabled: bool) -> None:
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


def set_blog_agent_enabled_guarded(
    *,
    agent_key: str,
    enabled: bool,
    actor_id: int,
    request_id: str,
) -> dict[str, Any]:
    normalized_key = str(agent_key or "").strip().lower()
    if normalized_key != "ai_blog_agent":
        raise PermissionError("Only AI Blog Agent control is enabled in this phase.")

    with session_scope() as session:
        current = session.execute(
            text(
                """
                SELECT agent_key, display_name, is_enabled, status
                FROM public.ai_agents
                WHERE agent_key = :agent_key
                FOR UPDATE
                """
            ),
            {"agent_key": normalized_key},
        ).mappings().first()
        if current is None:
            raise ValueError("AI Blog Agent is not configured.")

        previous_enabled = bool(current["is_enabled"])
        requested_enabled = bool(enabled)
        changed = previous_enabled != requested_enabled
        if changed:
            session.execute(
                text(
                    """
                    UPDATE public.ai_agents
                    SET is_enabled = :enabled,
                        updated_at = NOW()
                    WHERE agent_key = :agent_key
                    """
                ),
                {"agent_key": normalized_key, "enabled": requested_enabled},
            )

        session.execute(
            text(
                """
                INSERT INTO public.admin_auth_audit_events (
                    user_id, event_type, outcome, request_id, details
                ) VALUES (
                    :user_id, 'AI_BLOG_AGENT_ENABLED_STATE_CHANGED', 'SUCCESS',
                    :request_id, CAST(:details AS JSONB)
                )
                """
            ),
            {
                "user_id": int(actor_id) if actor_id is not None else None,
                "request_id": str(request_id or "unknown")[:128],
                "details": json.dumps(
                    {
                        "agent_key": normalized_key,
                        "previous_enabled": previous_enabled,
                        "requested_enabled": requested_enabled,
                        "changed": changed,
                    }
                ),
            },
        )

    return {
        "agent_key": normalized_key,
        "display_name": str(current["display_name"]),
        "enabled": requested_enabled,
        "previous_enabled": previous_enabled,
        "changed": changed,
        "status": str(current["status"] or "UNKNOWN"),
    }


def recover_stale_blog_agent_run_guarded(
    *,
    actor_id: int | None,
    request_id: str,
    stale_after_minutes: int = 60,
) -> StaleAgentRecoveryResult:
    """Recover only a clearly stale Blog Agent reservation.

    The agent and its newest RUNNING run are locked in one transaction. A
    recent run is never stolen, and the old run is retained as ERROR with an
    audit event rather than being deleted. Recovery also restores the Blog
    Agent to the executable enabled/IDLE state needed for a subsequent draft.
    """
    if stale_after_minutes < 5 or stale_after_minutes > 7 * 24 * 60:
        raise ValueError("stale_after_minutes must be between 5 and 10080.")

    normalized_key = "ai_blog_agent"
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=stale_after_minutes)
    recovery_reason = (
        f"Recovered stale RUNNING ai_blog_agent execution; no completion "
        f"after {stale_after_minutes} minutes."
    )

    with session_scope() as session:
        agent = session.execute(
            text(
                """
                SELECT id, agent_key, is_enabled, status
                FROM public.ai_agents
                WHERE agent_key = :agent_key
                FOR UPDATE
                """
            ),
            {"agent_key": normalized_key},
        ).mappings().first()
        if agent is None:
            raise ValueError("AI Blog Agent is not configured.")

        run = session.execute(
            text(
                """
                SELECT id, started_at
                FROM public.ai_agent_runs
                WHERE agent_id = :agent_id AND status = 'RUNNING'
                ORDER BY started_at DESC NULLS LAST, id DESC
                LIMIT 1
                FOR UPDATE
                """
            ),
            {"agent_id": agent["id"]},
        ).mappings().first()

        started_at = run["started_at"] if run else None
        if (
            str(agent["status"] or "").upper() != "RUNNING"
            or run is None
            or started_at is None
            or started_at > cutoff
        ):
            return StaleAgentRecoveryResult(
                agent_key=normalized_key,
                recovered=False,
                run_id=int(run["id"]) if run else None,
                previous_enabled=bool(agent["is_enabled"]),
                status=str(agent["status"] or "UNKNOWN"),
                reason="No clearly stale RUNNING Blog Agent execution was found.",
            )

        session.execute(
            text(
                """
                UPDATE public.ai_agent_runs
                SET status = 'ERROR',
                    finished_at = NOW(),
                    error_message = :reason,
                    duration_ms = LEAST(
                        CAST(EXTRACT(EPOCH FROM (NOW() - started_at)) * 1000 AS NUMERIC),
                        2147483647
                    )::INTEGER,
                    result_summary = :summary
                WHERE id = :run_id AND status = 'RUNNING'
                """
            ),
            {
                "run_id": int(run["id"]),
                "reason": recovery_reason,
                "summary": "Stale execution recovered by guarded admin action.",
            },
        )
        session.execute(
            text(
                """
                UPDATE public.ai_agents
                SET is_enabled = TRUE,
                    status = 'IDLE',
                    last_error = :reason,
                    updated_at = NOW()
                WHERE id = :agent_id AND status = 'RUNNING'
                """
            ),
            {"agent_id": agent["id"], "reason": recovery_reason},
        )
        session.execute(
            text(
                """
                INSERT INTO public.admin_auth_audit_events (
                    user_id, event_type, outcome, request_id, details
                ) VALUES (
                    :user_id, 'AI_BLOG_AGENT_STALE_RUN_RECOVERED', 'SUCCESS',
                    :request_id, CAST(:details AS JSONB)
                )
                """
            ),
            {
                "user_id": int(actor_id) if actor_id is not None else None,
                "request_id": str(request_id or "unknown")[:128],
                "details": json.dumps(
                    {
                        "agent_key": normalized_key,
                        "run_id": int(run["id"]),
                        "previous_enabled": bool(agent["is_enabled"]),
                        "stale_after_minutes": stale_after_minutes,
                        "recovery_reason": recovery_reason,
                    }
                ),
            },
        )

    return StaleAgentRecoveryResult(
        agent_key=normalized_key,
        recovered=True,
        run_id=int(run["id"]),
        previous_enabled=bool(agent["is_enabled"]),
        status="IDLE",
        reason=recovery_reason,
    )


def resolve_agent_key_from_number(number: int | str) -> str:
    try:
        selected = int(str(number).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError("AI number must be numeric.") from exc
    for agent_number, agent_key, _ in AI_AGENT_CONTROL_NUMBERS:
        if selected == agent_number:
            return agent_key
    raise ValueError(f"Unknown AI number: {selected}")


def set_ai_agent_enabled_by_number(number: int | str, enabled: bool) -> dict[str, Any]:
    agent_key = resolve_agent_key_from_number(number)
    set_ai_agent_enabled(agent_key, enabled)
    return {
        "number": int(str(number).strip()),
        "agent_key": agent_key,
        "display_name": _agent_display_name(agent_key),
        "enabled": bool(enabled),
    }


def agent_control_help_text() -> str:
    lines = ["AI ON/OFF controls:"]
    for number, _, display_name in AI_AGENT_CONTROL_NUMBERS:
        lines.append(f"{number}. {display_name}")
    return "\n".join(lines)


def _agent_display_name(agent_key: str) -> str:
    for _, mapped_key, display_name in AI_AGENT_CONTROL_NUMBERS:
        if mapped_key == agent_key:
            return display_name
    return agent_key.replace("_", " ").title()


def run_ai_agent(
    agent_key: str,
    triggered_by: int | None,
    supabase: Any,
    payload: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    """Run one exact enabled agent; never substitute another worker."""
    clean_key = str(agent_key or "").strip()
    if not clean_key:
        return False, "Exact agent key is required."

    runner = RUNNERS.get(clean_key)
    if runner is None:
        return False, f"Exact agent '{clean_key}' has no production runner configured."

    if clean_key == "ai_blog_agent":
        try:
            recover_stale_blog_agent_run_guarded(
                actor_id=triggered_by,
                request_id=f"worker-stale-recovery:{datetime.now(timezone.utc).isoformat()}",
            )
        except Exception:
            logger.exception("AI Blog Agent stale-run recovery failed closed")
            return False, "AI Blog Agent stale-run recovery is temporarily unavailable."

    start = _start_run(clean_key, triggered_by)
    if start.run_id is None:
        return False, start.reason or f"Exact agent '{clean_key}' cannot execute."

    started_at = datetime.now(timezone.utc)
    try:
        result_message = runner(payload or {})
        if not isinstance(result_message, str) or not result_message.strip():
            raise RuntimeError("Production runner returned no verifiable result.")
        result_message = result_message.strip()
    except Exception as exc:
        error = str(exc).strip() or exc.__class__.__name__
        logger.exception("AI agent run failed: {}", clean_key)
        _finish_run(
            start.run_id,
            clean_key,
            succeeded=False,
            error=error,
            result=None,
            started_at=started_at,
        )
        return False, error

    _finish_run(
        start.run_id,
        clean_key,
        succeeded=True,
        error=None,
        result=result_message,
        started_at=started_at,
    )
    return True, result_message


def _start_run(agent_key: str, triggered_by: int | None) -> AgentStartResult:
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
            state = (
                session.execute(
                    text(
                        """
                        SELECT agent_key, is_enabled, status
                        FROM public.ai_agents
                        WHERE agent_key = :agent_key
                        """
                    ),
                    {"agent_key": agent_key},
                )
                .mappings()
                .first()
            )
            if state is None:
                return AgentStartResult(None, f"Exact agent '{agent_key}' is not registered in the shared registry.")
            if not bool(state["is_enabled"]):
                return AgentStartResult(None, f"Exact agent '{agent_key}' is disabled in the shared registry.")
            if str(state.get("status") or "").upper() == "RUNNING":
                return AgentStartResult(None, f"Exact agent '{agent_key}' is already running.")
            return AgentStartResult(None, f"Exact agent '{agent_key}' could not be reserved for execution.")

        run_id = session.execute(
            text(
                """
                INSERT INTO public.ai_agent_runs (agent_id, status, triggered_by)
                VALUES (:agent_id, 'RUNNING', :triggered_by)
                RETURNING id
                """
            ),
            {"agent_id": agent["id"], "triggered_by": triggered_by},
        ).scalar_one()
    return AgentStartResult(int(run_id), None)


def _finish_run(
    run_id: int,
    agent_key: str,
    succeeded: bool,
    error: str | None,
    result: str | None,
    started_at: datetime,
) -> None:
    safe_error = error[:_MAX_ERROR_LENGTH] if error else None
    agent_status = "IDLE" if succeeded else "ERROR"
    run_status = "SUCCESS" if succeeded else "ERROR"
    duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
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
