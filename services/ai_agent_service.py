"""Admin-only AI-agent state, audit history, and manual execution."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from loguru import logger
from sqlalchemy import text

from agent_bot import run_pipeline_once
from core.database import session_scope
from services.google_sheets import GoogleSheetsService
from services.market_data import MarketDataService
from services.telegram_service import TelegramService


AgentRunner = Callable[[Any], str]
_MAX_ERROR_LENGTH = 2_000


def list_ai_agents() -> list[dict[str, Any]]:
    """Return agent status records in their configured display order."""
    with session_scope() as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT agent_key, display_name, is_enabled, status,
                           last_run_at, last_error
                    FROM public.ai_agents
                    ORDER BY display_order, display_name
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
) -> tuple[bool, str]:
    """Run one enabled agent and persist its complete execution state."""
    run_id = _start_run(agent_key, triggered_by)
    if run_id is None:
        return False, "Agent is disabled, unavailable, or already running."

    try:
        runner = _RUNNERS.get(agent_key)
        if runner is None:
            raise RuntimeError(
                "No production runner is configured for this agent."
            )
        result_message = runner(supabase)
    except Exception as exc:
        error = str(exc).strip() or exc.__class__.__name__
        logger.exception("Manual AI agent run failed: {}", agent_key)
        _finish_run(run_id, agent_key, succeeded=False, error=error)
        return False, error

    _finish_run(run_id, agent_key, succeeded=True, error=None)
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
) -> None:
    """Finalize the run audit row and current agent status."""
    safe_error = error[:_MAX_ERROR_LENGTH] if error else None
    agent_status = "IDLE" if succeeded else "ERROR"
    run_status = "SUCCESS" if succeeded else "ERROR"
    with session_scope() as session:
        session.execute(
            text(
                """
                UPDATE public.ai_agent_runs
                SET status = :run_status,
                    finished_at = NOW(),
                    error_message = :error
                WHERE id = :run_id
                """
            ),
            {
                "run_status": run_status,
                "error": safe_error,
                "run_id": run_id,
            },
        )
        session.execute(
            text(
                """
                UPDATE public.ai_agents
                SET status = :agent_status,
                    last_run_at = NOW(),
                    last_error = :error,
                    updated_at = NOW()
                WHERE agent_key = :agent_key
                """
            ),
            {
                "agent_status": agent_status,
                "error": safe_error,
                "agent_key": agent_key,
            },
        )


def _run_signal_agent(supabase: Any) -> str:
    """Execute the production Sheets-to-Telegram signal pipeline once."""
    sheets: GoogleSheetsService | None
    try:
        sheets = GoogleSheetsService()
    except Exception:
        logger.exception(
            "Google Sheets unavailable during manual Signal Agent run"
        )
        sheets = None
    run_pipeline_once(
        sheets=sheets,
        market_data=MarketDataService(supabase),
        telegram=TelegramService(supabase),
    )
    return "Signal Agent completed one production pipeline cycle."


def _run_telegram_agent(supabase: Any) -> str:
    """Deliver pending production Telegram signals once."""
    delivered = TelegramService(supabase).broadcast_pending_signals()
    return f"Telegram Reply Agent delivered {delivered} pending signal(s)."


_RUNNERS: dict[str, AgentRunner] = {
    "signal_agent": _run_signal_agent,
    "telegram_reply_agent": _run_telegram_agent,
}
