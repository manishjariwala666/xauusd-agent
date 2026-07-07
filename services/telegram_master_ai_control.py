"""Telegram admin command control for the Master AI Orchestrator.

Two-bot architecture:

* ``TELEGRAM_BOT_TOKEN`` remains dedicated to the public Buy/Sell Signal Bot.
* ``MASTER_AI_TELEGRAM_BOT_TOKEN`` is dedicated to the private Master AI Admin Bot.
* ``/master`` commands are processed only in the Master AI bot context.
* The signal/reply bot explicitly suppresses ``/master`` so it never replies to
  admin commands and never leaks internals to public users.
"""

from __future__ import annotations

from dataclasses import dataclass
from os import getenv
from typing import Any, Callable, Iterable, Literal

from services.master_orchestrator import (
    OrchestrationProgress,
    create_and_start_master_task,
    list_orchestration_runs,
)
from services.orchestration_redaction import redact_value

SAFE_TELEGRAM_ERROR = "⚠️ Service temporarily unavailable. Please try again later."
MASTER_COMMAND = "/master"

SIGNAL_BOT = "SIGNAL"
MASTER_AI_BOT = "MASTER_AI"
SIGNAL_WEBHOOK_PATH = "/webhooks/telegram"
MASTER_WEBHOOK_PATH = "/webhooks/telegram/master"
SIGNAL_BOT_TOKEN_ENV = "TELEGRAM_BOT_TOKEN"
MASTER_AI_BOT_TOKEN_ENV = "MASTER_AI_TELEGRAM_BOT_TOKEN"

TelegramBotRole = Literal["SIGNAL", "MASTER_AI"]
Sender = Callable[[int | str, str], None]
Runner = Callable[..., OrchestrationProgress]
StatusLoader = Callable[..., list[dict[str, Any]]]


@dataclass(frozen=True)
class MasterTelegramCommandResult:
    """Result returned to the Telegram webhook integration layer."""

    handled: bool
    response_text: str | None = None
    chat_id: int | str | None = None
    status: str = "IGNORED"
    run_id: int | None = None
    task_type: str | None = None
    bot_role: str | None = None


@dataclass(frozen=True)
class MasterRunTarget:
    """Safe mapping from Telegram command alias to a Master AI task."""

    task_type: str
    title: str
    objective: str
    parallel: bool = False
    max_attempts: int = 2
    risk_level: str = "LOW"


RUN_TARGETS: dict[str, MasterRunTarget] = {
    "daily_content": MasterRunTarget(
        task_type="DAILY_CONTENT",
        title="Daily content package",
        objective=(
            "Create the daily public content workflow using the appropriate "
            "content, blog, image, market, and notification worker agents."
        ),
        parallel=True,
    ),
    "signal": MasterRunTarget(
        task_type="SIGNAL",
        title="XAUUSD signal workflow",
        objective="Run the XAUUSD market signal workflow using signal or market worker agents.",
    ),
    "blog": MasterRunTarget(
        task_type="BLOG",
        title="AI blog workflow",
        objective="Run the AI blog/content worker agent workflow.",
    ),
    "image": MasterRunTarget(
        task_type="IMAGE",
        title="Image generation workflow",
        objective="Run the image/content creative worker agent workflow.",
    ),
}


def try_handle_telegram_update(
    update: dict[str, Any],
    *,
    sender: Sender | None = None,
    supabase: Any | None = None,
    runner: Runner = create_and_start_master_task,
    status_loader: StatusLoader = list_orchestration_runs,
    bot_role: TelegramBotRole = MASTER_AI_BOT,
) -> MasterTelegramCommandResult:
    """Safely route one Telegram update under the two-bot architecture.

    ``bot_role=MASTER_AI`` is for ``/webhooks/telegram/master`` and treats every
    update as handled so public buy/sell logic can never run in the Master AI
    bot. ``bot_role=SIGNAL`` is for the existing ``/webhooks/telegram`` endpoint;
    it silently consumes ``/master`` commands and returns ``handled=False`` for
    all other messages so the existing reply/signal bot behavior is unchanged.
    """
    parsed = _extract_message(update)
    if parsed is None:
        return MasterTelegramCommandResult(
            handled=bot_role == MASTER_AI_BOT,
            status="IGNORED_EMPTY_UPDATE",
            bot_role=bot_role,
        )

    text = parsed["text"]
    if bot_role == SIGNAL_BOT:
        if is_master_command(text):
            # Public signal/reply bot must not respond to Master AI commands and
            # must not pass them to the existing Telegram reply agent.
            return MasterTelegramCommandResult(
                handled=True,
                response_text=None,
                chat_id=parsed.get("chat_id"),
                status="IGNORED_WRONG_BOT",
                bot_role=SIGNAL_BOT,
            )
        return MasterTelegramCommandResult(
            handled=False,
            chat_id=parsed.get("chat_id"),
            status="PASS_TO_SIGNAL_BOT",
            bot_role=SIGNAL_BOT,
        )

    # Master AI bot endpoint: do not allow public signal/reply behavior here.
    if not is_master_command(text):
        return MasterTelegramCommandResult(
            handled=True,
            response_text=None,
            chat_id=parsed.get("chat_id"),
            status="IGNORED_NON_MASTER_COMMAND",
            bot_role=MASTER_AI_BOT,
        )

    result = handle_master_command_text(
        text=text,
        telegram_user_id=parsed.get("telegram_user_id"),
        chat_id=parsed.get("chat_id"),
        supabase=supabase,
        runner=runner,
        status_loader=status_loader,
    )
    result = MasterTelegramCommandResult(
        handled=result.handled,
        response_text=result.response_text,
        chat_id=result.chat_id,
        status=result.status,
        run_id=result.run_id,
        task_type=result.task_type,
        bot_role=MASTER_AI_BOT,
    )
    if sender is not None and result.response_text is not None and result.chat_id is not None:
        try:
            sender(result.chat_id, result.response_text)
        except Exception:
            # Telegram send failures must not expose tokens/raw exceptions.
            return MasterTelegramCommandResult(
                handled=True,
                response_text=SAFE_TELEGRAM_ERROR,
                chat_id=result.chat_id,
                status="ERROR",
                run_id=result.run_id,
                task_type=result.task_type,
                bot_role=MASTER_AI_BOT,
            )
    return result


def handle_master_command_text(
    *,
    text: str,
    telegram_user_id: int | str | None,
    chat_id: int | str | None,
    supabase: Any | None = None,
    runner: Runner = create_and_start_master_task,
    status_loader: StatusLoader = list_orchestration_runs,
) -> MasterTelegramCommandResult:
    """Parse and execute one Telegram Master AI admin command."""
    if not is_master_command(text):
        return MasterTelegramCommandResult(handled=False, chat_id=chat_id)

    if not _is_authorized_admin(telegram_user_id):
        return MasterTelegramCommandResult(
            handled=True,
            response_text="⛔ Unauthorized.",
            chat_id=chat_id,
            status="UNAUTHORIZED",
        )

    try:
        command, target = parse_master_command(text)
        if command in {"help", ""}:
            return MasterTelegramCommandResult(
                handled=True,
                response_text=help_text(),
                chat_id=chat_id,
                status="OK",
            )
        if command == "status":
            return MasterTelegramCommandResult(
                handled=True,
                response_text=_status_text(status_loader(limit=5)),
                chat_id=chat_id,
                status="OK",
            )
        if command == "run":
            if target not in RUN_TARGETS:
                return MasterTelegramCommandResult(
                    handled=True,
                    response_text=help_text(),
                    chat_id=chat_id,
                    status="INVALID_COMMAND",
                )
            run_target = RUN_TARGETS[target]
            progress = runner(
                task_type=run_target.task_type,
                title=run_target.title,
                input_payload={
                    "objective": run_target.objective,
                    "telegram_command": f"/master run {target}",
                    "telegram_target": target,
                    "telegram_user_id": str(telegram_user_id or ""),
                    "parallel": run_target.parallel,
                    "max_attempts": run_target.max_attempts,
                    "risk_level": run_target.risk_level,
                },
                requested_by=None,
                source="TELEGRAM_MASTER_COMMAND",
                supabase=supabase,
            )
            _record_command_memory_and_event(
                run_id=progress.run_id,
                command=f"/master run {target}",
                status=progress.status,
                telegram_user_id=telegram_user_id,
                target=target,
            )
            return MasterTelegramCommandResult(
                handled=True,
                response_text=_run_started_text(target, progress),
                chat_id=chat_id,
                status=progress.status,
                run_id=progress.run_id,
                task_type=run_target.task_type,
            )
    except Exception:
        # User-facing Telegram errors are intentionally fixed and generic.
        return MasterTelegramCommandResult(
            handled=True,
            response_text=SAFE_TELEGRAM_ERROR,
            chat_id=chat_id,
            status="ERROR",
        )

    return MasterTelegramCommandResult(
        handled=True,
        response_text=help_text(),
        chat_id=chat_id,
        status="INVALID_COMMAND",
    )


def is_master_command(text: str | None) -> bool:
    """Return True for /master commands, including bot-name suffixes."""
    if not text:
        return False
    first = str(text).strip().split(maxsplit=1)[0].lower()
    return first == MASTER_COMMAND or first.startswith(f"{MASTER_COMMAND}@")


def parse_master_command(text: str) -> tuple[str, str | None]:
    """Parse supported Master AI command shape."""
    parts = str(text or "").strip().split()
    if not parts or not is_master_command(parts[0]):
        return "", None
    if len(parts) == 1:
        return "help", None
    command = parts[1].lower()
    target = parts[2].lower() if len(parts) >= 3 else None
    return command, target


def help_text() -> str:
    return (
        "🤖 Master AI admin commands:\n"
        "/master status\n"
        "/master run daily_content\n"
        "/master run signal\n"
        "/master run blog\n"
        "/master run image\n"
        "/master help"
    )


def get_telegram_bot_token_env(bot_role: TelegramBotRole) -> str:
    """Return the environment variable name for a bot role without reading it."""
    if bot_role == MASTER_AI_BOT:
        return MASTER_AI_BOT_TOKEN_ENV
    return SIGNAL_BOT_TOKEN_ENV


def _status_text(rows: Iterable[dict[str, Any]]) -> str:
    safe_rows = list(rows or [])
    if not safe_rows:
        return "🤖 Master AI status\nNo orchestration runs yet."

    lines = ["🤖 Master AI status"]
    for row in safe_rows[:5]:
        run_id = row.get("run_id") or row.get("id") or "—"
        status = _safe_word(row.get("status") or "UNKNOWN")
        task_type = _safe_word(row.get("task_type") or "TASK")
        completed = int(row.get("completed_steps") or 0)
        total = int(row.get("total_steps") or 0)
        lines.append(f"#{run_id} · {task_type} · {status} · {completed}/{total}")
    return "\n".join(lines)


def _run_started_text(target: str, progress: OrchestrationProgress) -> str:
    return (
        "🤖 Master AI orchestration accepted.\n"
        f"Task: {target}\n"
        f"Run: #{progress.run_id}\n"
        f"Status: {_safe_word(progress.status)}\n"
        f"Progress: {progress.completed_steps}/{progress.total_steps}"
    )


def _extract_message(update: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(update, dict):
        return None
    message = (
        update.get("message")
        or update.get("edited_message")
        or update.get("channel_post")
        or update.get("callback_query", {}).get("message")
    )
    if not isinstance(message, dict):
        return None
    text = message.get("text") or message.get("caption") or ""
    if not text:
        return None
    chat = message.get("chat") if isinstance(message.get("chat"), dict) else {}
    sender = message.get("from") if isinstance(message.get("from"), dict) else {}
    return {
        "text": str(text),
        "chat_id": chat.get("id"),
        "telegram_user_id": sender.get("id"),
    }


def _is_authorized_admin(telegram_user_id: int | str | None) -> bool:
    if telegram_user_id is None:
        return False
    allowed = _allowed_admin_user_ids()
    return str(telegram_user_id).strip() in allowed if allowed else False


def _allowed_admin_user_ids() -> set[str]:
    """Load Telegram admin IDs from TELEGRAM_ADMIN_USER_ID(S) only."""
    values: list[str] = []
    for name in ("TELEGRAM_ADMIN_USER_ID", "TELEGRAM_ADMIN_USER_IDS"):
        raw = getenv(name)
        if raw:
            values.extend(raw.replace(";", ",").split(","))

    try:
        from config import get_settings

        settings = get_settings()
        for attr in ("telegram_admin_user_id", "telegram_admin_user_ids"):
            raw = getattr(settings, attr, None)
            if raw:
                if isinstance(raw, (list, tuple, set)):
                    values.extend(str(item) for item in raw)
                else:
                    values.extend(str(raw).replace(";", ",").split(","))
    except Exception:
        pass

    return {value.strip() for value in values if value and value.strip()}


def _record_command_memory_and_event(
    *,
    run_id: int,
    command: str,
    status: str,
    telegram_user_id: int | str | None,
    target: str,
) -> None:
    """Best-effort audit entry for Telegram command execution.

    This function writes only redacted metadata. Failures are intentionally
    ignored so Telegram command handling never leaks database exceptions.
    """
    try:
        import json
        from sqlalchemy import text
        from core.database import session_scope

        metadata = redact_value(
            {
                "command": command,
                "status": status,
                "telegram_user_id": str(telegram_user_id or ""),
                "target": target,
                "bot_role": MASTER_AI_BOT,
            }
        )
        with session_scope() as session:
            session.execute(
                text(
                    """
                    INSERT INTO public.master_ai_memory_entries (
                        run_id, entry_type, summary, data_redacted, created_by
                    ) VALUES (
                        :run_id, 'DECISION', :summary, CAST(:metadata AS JSONB),
                        'TELEGRAM_MASTER_COMMAND'
                    )
                    """
                ),
                {
                    "run_id": int(run_id),
                    "summary": f"Telegram admin command executed: {command}",
                    "metadata": json.dumps(metadata),
                },
            )
            session.execute(
                text(
                    """
                    INSERT INTO public.master_ai_events (
                        run_id, event_type, severity, message, metadata_redacted
                    ) VALUES (
                        :run_id, 'TELEGRAM_MASTER_COMMAND', 'INFO',
                        :message, CAST(:metadata AS JSONB)
                    )
                    """
                ),
                {
                    "run_id": int(run_id),
                    "message": f"Telegram command accepted for target: {target}",
                    "metadata": json.dumps(metadata),
                },
            )
    except Exception:
        return


def _safe_word(value: Any) -> str:
    text = str(value or "").strip().upper()
    return "".join(char for char in text if char.isalnum() or char in {"_", "-"})[:40] or "UNKNOWN"
