"""Telegram admin command control for the Master AI Orchestrator.

Two-bot architecture:

* ``TELEGRAM_BOT_TOKEN`` remains dedicated to the public Buy/Sell Signal Bot.
* ``MASTER_AI_TELEGRAM_BOT_TOKEN`` is dedicated to the private Master AI Admin Bot.
* ``/master`` commands are processed only in the Master AI bot context.
* The signal/reply bot explicitly suppresses ``/master`` so it never replies to
  admin commands and never leaks internals to public users.
"""

from __future__ import annotations

from services.google_sheets_service import append_master_log
from services.master_ai_chat_service import generate_master_ai_reply
from services.ai_agent_service import (
    agent_control_help_text,
    list_ai_agents,
    set_ai_agent_enabled_by_number,
)

from dataclasses import dataclass
from os import getenv
from typing import Any, Callable, Iterable, Literal

from services.master_orchestrator import (
    OrchestrationProgress,
    create_and_start_master_task,
    list_orchestration_runs,
)
from services.orchestration_redaction import redact_value
from services.url_service import public_content_url, public_website_base_url
from services.whatsapp_service import WhatsAppService

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
        objective=(
            "Run the SEO blog/content workflow. Include title, meta title, "
            "meta description, slug, category, region, topic, featured image "
            "brief, thumbnail brief, and landscape card preview metadata."
        ),
    ),
    "image": MasterRunTarget(
        task_type="IMAGE",
        title="Image generation workflow",
        objective="Run the image/content creative worker agent workflow.",
    ),
}

RUN_TARGET_ALIASES: dict[str, str] = {
    "daily": "daily_content",
    "daily_content": "daily_content",
    "dailycontent": "daily_content",
    "dialy_content": "daily_content",
    "daliy_content": "daily_content",
    "daily_post": "daily_content",
    "content_package": "daily_content",
    "signal": "signal",
    "signals": "signal",
    "xauusd_signal": "signal",
    "buy_sell": "signal",
    "blog": "blog",
    "seo": "blog",
    "seo_blog": "blog",
    "article": "blog",
    "post": "blog",
    "news": "blog",
    "content": "blog",
    "market_news": "blog",
    "crypto_news": "blog",
    "xauusd_news": "blog",
    "image": "image",
    "img": "image",
    "photo": "image",
    "thumbnail": "image",
    "creative": "image",
}

REGION_KEYWORDS: dict[str, str] = {
    "usa": "USA",
    "us": "USA",
    "america": "USA",
    "europe": "Europe",
    "eu": "Europe",
    "japan": "Japan",
    "india": "India",
    "global": "Global",
    "world": "Global",
}

TOPIC_KEYWORDS: dict[str, str] = {
    "xauusd": "XAUUSD",
    "gold": "Gold",
    "crypto": "Crypto",
    "bitcoin": "Crypto",
    "btc": "Crypto",
    "forex": "Forex",
    "market": "Market",
    "stock": "Stock Market",
    "seo": "SEO",
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

    # Master AI bot endpoint: every message is handled here so normal admin
    # text can receive a clear reply instead of silently falling through.
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


def _log_master_command_to_sheet(
    *,
    command: str,
    status: str,
    run_id: int | str | None = None,
    chat_id: int | str | None = None,
    telegram_user_id: int | str | None = None,
    notes: str = "",
) -> None:
    """Best-effort Google Sheet log. Never break Telegram command flow."""
    try:
        append_master_log(
            command=command,
            status=status,
            run_id=run_id,
            chat_id=chat_id,
            user_id=telegram_user_id,
            notes=notes,
        )
    except Exception:
        return


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
    original_text = str(text or "").strip()
    text = _normalize_master_command_text(original_text)

    if not _is_authorized_admin(telegram_user_id):
        return MasterTelegramCommandResult(
            handled=True,
            response_text="⛔ Unauthorized.",
            chat_id=chat_id,
            status="UNAUTHORIZED",
        )

    if not is_master_command(text):
        live_status_target = _infer_live_status_target(original_text)
        if live_status_target:
            return MasterTelegramCommandResult(
                handled=True,
                response_text=_status_text(live_status_target),
                chat_id=chat_id,
                status="OK",
            )

        inferred_target = _infer_run_target(text)
        if inferred_target and _looks_like_master_natural_command(text):
            text = f"{MASTER_COMMAND} run {inferred_target}"
        else:
            if _looks_like_signal_text(original_text):
                return MasterTelegramCommandResult(
                    handled=True,
                    response_text=_unknown_master_text_response(),
                    chat_id=chat_id,
                    status="IGNORED_NON_MASTER_COMMAND",
                )

            return MasterTelegramCommandResult(
                handled=True,
                response_text=generate_master_ai_reply(original_text),
                chat_id=chat_id,
                status="AI_CHAT_RESPONSE",
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
            _log_master_command_to_sheet(
                command=f"/master status {target or ''}".strip(),
                status="OK",
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
            )
            return MasterTelegramCommandResult(
                handled=True,
                response_text=_status_text(target),
                chat_id=chat_id,
                status="OK",
            )

        if command in {"news", "xauusd", "buy", "sell"}:
            prompt = {
                "news": "Latest important market and business news ka concise summary do. Koi content publish mat karo.",
                "xauusd": "XAUUSD ka current market context aur neutral analysis do. Live price unavailable ho to clearly batao. Koi trade execute ya signal publish mat karo.",
                "buy": "XAUUSD ke buy-side factors aur risks explain karo. Guaranteed signal mat do aur koi trade execute mat karo.",
                "sell": "XAUUSD ke sell-side factors aur risks explain karo. Guaranteed signal mat do aur koi trade execute mat karo.",
            }[command]
            return MasterTelegramCommandResult(
                handled=True,
                response_text=generate_master_ai_reply(prompt),
                chat_id=chat_id,
                status="AI_CHAT_RESPONSE",
            )
        if command == "test" and str(target or "").strip().lower() in {
            "whatsapp",
            "wa",
        }:
            try:
                message_id = WhatsAppService().send_text(
                    "",
                    "✅ VenusRealm Green API WhatsApp group test successful.",
                )
                response = (
                    "✅ WhatsApp group test message sent successfully.\n"
                    f"Message ID: {message_id}"
                )
                status = "OK"
            except Exception as exc:
                print(
                    f"[master-whatsapp-test] error={type(exc).__name__}"
                )
                response = (
                    "⚠️ WhatsApp group test failed. "
                    "Railway logs me latest WhatsApp error check karein."
                )
                status = "ERROR"

            return MasterTelegramCommandResult(
                handled=True,
                response_text=response,
                chat_id=chat_id,
                status=status,
            )

        if command in {"on", "off", "list_ai"}:
            response = _handle_ai_toggle_command(command, target)
            _log_master_command_to_sheet(
                command=f"/master {command} {target or ''}".strip(),
                status="OK",
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
            )
            return MasterTelegramCommandResult(
                handled=True,
                response_text=response,
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
            context = _command_context(original_text=original_text, target=target)
            progress = runner(
                task_type=run_target.task_type,
                title=run_target.title,
                input_payload={
                    "objective": _objective_with_context(run_target.objective, context),
                    "telegram_command": f"/master run {target}",
                    "telegram_raw_text": original_text,
                    "telegram_target": target,
                    "telegram_context": context,
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
            _log_master_command_to_sheet(
                command=f"/master run {target}",
                status=progress.status,
                run_id=progress.run_id,
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                notes=f"target={target}",
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
    """Return True for /master commands, including common typo variants."""
    if not text:
        return False
    first = str(text).strip().split(maxsplit=1)[0].lower()
    command = first.split("@", 1)[0]
    return command in {MASTER_COMMAND, "/mastr", "/mster", "master", "mastr"}


def parse_master_command(text: str) -> tuple[str, str | None]:
    """Parse exact, typo, alias, and natural Master AI command shapes."""
    normalized = _normalize_master_command_text(text)
    parts = str(normalized or "").strip().split()
    if not parts or not is_master_command(parts[0]):
        return "", None
    if len(parts) == 1:
        return "help", None

    remainder = " ".join(parts[1:]).strip()
    if not remainder:
        return "help", None

    first, _, tail = remainder.partition(" ")
    command = first.lower().strip()
    tail = tail.strip()

    if command in {"help", "h", "?", "commands"}:
        return "help", None
    if command in {"status", "st", "health"}:
        return "status", tail or None
    if command in {"list", "show"} and tail.lower() in {"ai", "ais", "agents"}:
        return "list_ai", None
    if command in {"on", "off", "enable", "disable"}:
        ai_number = _extract_ai_control_number(tail)
        if ai_number is None:
            return "list_ai", None
        normalized_command = "on" if command in {"on", "enable"} else "off"
        return normalized_command, ai_number
    if command in {"run", "start", "create", "make", "generate", "post", "publish", "do", "execute"}:
        target = _normalize_run_target(tail)
        return ("run", target) if target else ("help", None)

    target = _normalize_run_target(remainder)
    if target:
        return "run", target

    return command, tail or None


def _extract_ai_control_number(value: str | None) -> str | None:
    """Extract the owner-facing AI number from commands like 'ai 1'."""
    raw = str(value or "").strip().lower()
    if not raw:
        return None
    tokens = [
        token.strip("#.,:;()[]")
        for token in raw.replace("/", " ").replace("-", " ").split()
    ]
    if tokens and tokens[0] in {"ai", "agent", "agents", "bot"}:
        tokens = tokens[1:]
    for token in tokens:
        if token.isdigit():
            return token
    return None


def _handle_ai_toggle_command(command: str, target: str | None) -> str:
    """Execute a safe AI on/off command without exposing internals."""
    if command == "list_ai":
        return "🤖 " + agent_control_help_text()
    if not target:
        return "🤖 Send `/master list ai` to see AI numbers."
    try:
        result = set_ai_agent_enabled_by_number(
            target,
            enabled=(command == "on"),
        )
    except ValueError:
        return "🤖 Unknown AI number.\n" + agent_control_help_text()
    state = "ON" if result["enabled"] else "OFF"
    return (
        f"🤖 AI {result['number']} {state}\n"
        f"{result['display_name']} is now {state}."
    )


def _normalize_master_command_text(text: str | None) -> str:
    value = str(text or "").strip()
    if not value:
        return ""
    first, sep, rest = value.partition(" ")
    command = first.lower().split("@", 1)[0]
    if command in {"/mastr", "/mster", "master", "mastr"}:
        return f"{MASTER_COMMAND}{sep}{rest}".strip()
    return value


def _normalize_run_target(value: str | None) -> str | None:
    raw = str(value or "").strip().lower()
    if not raw:
        return None

    clean = raw.replace("-", "_").replace("/", " ").strip()
    compact = "_".join(clean.split())

    for candidate in (clean, compact, compact.replace("_", "")):
        if candidate in RUN_TARGET_ALIASES:
            return RUN_TARGET_ALIASES[candidate]

    if "daily" in clean and "content" in clean:
        return "daily_content"
    if any(word in clean for word in ("blog", "seo", "article", "post")):
        return "blog"
    if any(word in clean for word in ("signal", "buy sell", "buy/sell", "entry", "target", "sl", "tp")):
        return "signal"
    if any(word in clean for word in ("image", "photo", "thumbnail", "creative", "poster")) and not any(
        word in clean for word in ("blog", "seo", "news", "article", "post")
    ):
        return "image"
    if any(word in clean for word in (
        "blog", "seo", "news", "article", "post", "content",
        "crypto", "xauusd", "gold", "forex", "market", "usa",
        "europe", "japan", "india",
    )):
        return "blog"
    return None


def _infer_live_status_target(text: str | None) -> str | None:
    """Map natural owner questions to one live agent-status target."""
    value = str(text or "").strip().lower()
    if not value:
        return None

    status_intents = (
        "status",
        "on/off",
        "on hai",
        "off hai",
        "last run",
        "last error",
        "queue",
        "kab chala",
        "kab hua",
        "error kya",
    )
    if not any(intent in value for intent in status_intents):
        return None

    targets = (
        (("whatsapp", "wa "), "whatsapp"),
        (("announcement", "broadcast"), "announcement"),
        (("telegram",), "telegram"),
        (("signal", "xauusd"), "signal"),
        (("blog", "news"), "blog"),
    )
    for keywords, target in targets:
        if any(keyword in value for keyword in keywords):
            return target

    return None


def _infer_run_target(text: str | None) -> str | None:
    return _normalize_run_target(text)


def _looks_like_master_natural_command(text: str | None) -> bool:
    value = str(text or "").strip().lower()
    if not value:
        return False
    if is_master_command(value):
        return True
    if value in {"status", "help", "commands"}:
        return True

    # Do not treat public buy/sell signal text as a Master AI instruction.
    signal_only_terms = {"buy", "sell", "sl", "tp", "entry", "target"}
    words = {word.strip(".,:;!?()[]{}") for word in value.replace("/", " ").split()}
    if words & signal_only_terms and not any(
        intent in value
        for intent in (
            "run", "start", "create", "make", "generate", "post", "publish",
            "banao", "banavo", "chalao", "karo", "blog", "seo", "news",
            "article", "content", "image", "daily"
        )
    ):
        return False

    return any(
        intent in value
        for intent in (
            "run", "start", "create", "make", "generate", "post", "publish",
            "banao", "banavo", "chalao", "karo", "blog", "seo", "news",
            "article", "content", "image", "daily", "crypto", "xauusd",
            "gold", "forex", "usa", "europe", "japan", "india"
        )
    )


def _command_context(*, original_text: str, target: str) -> dict[str, Any]:
    value = str(original_text or "")
    lower = value.lower()

    regions: list[str] = []
    for keyword, region in REGION_KEYWORDS.items():
        if keyword in lower and region not in regions:
            regions.append(region)

    topics: list[str] = []
    for keyword, topic in TOPIC_KEYWORDS.items():
        if keyword in lower and topic not in topics:
            topics.append(topic)

    image_required = target in {"image", "blog", "daily_content"} or any(
        word in lower for word in ("image", "photo", "thumbnail", "poster", "creative", "landscape")
    )
    seo_enabled = target in {"blog", "daily_content"} or "seo" in lower

    return {
        "raw_request": value,
        "target": target,
        "regions": regions or (["Global"] if target in {"blog", "daily_content"} else []),
        "topics": topics,
        "seo_enabled": seo_enabled,
        "image_required": image_required,
        "admin_panel_layout": "landscape_card_with_small_thumbnail",
        "required_blog_fields": [
            "title",
            "meta_title",
            "meta_description",
            "slug",
            "category",
            "region",
            "topic",
            "featured_image",
            "thumbnail",
            "seo_keywords",
            "content_body",
            "status",
        ],
    }


def _objective_with_context(base_objective: str, context: dict[str, Any]) -> str:
    regions = ", ".join(context.get("regions") or []) or "Global"
    topics = ", ".join(context.get("topics") or []) or "General market"
    return (
        f"{base_objective}\n"
        f"User request: {context.get('raw_request') or ''}\n"
        f"Topics: {topics}\n"
        f"Regions: {regions}\n"
        f"SEO enabled: {bool(context.get('seo_enabled'))}\n"
        f"Image required: {bool(context.get('image_required'))}\n"
        "When creating website/blog content, prepare admin-ready metadata: "
        "title, meta title, meta description, slug, category, region, topic, "
        "SEO keywords, featured image brief, thumbnail brief, landscape card preview, "
        "content body, and draft/published status."
    )


def help_text() -> str:
    return (
        "🤖 Master AI admin commands:\n"
        "/master status\n"
        "/master list ai\n"
        "/master on ai 1\n"
        "/master off ai 1\n"
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


def _status_text(target: str | None = None) -> str:
    """Return a clean owner-facing status menu instead of failed-run history."""
    requested = str(target or "").strip().lower()

    if not requested:
        return (
            "🤖 Master AI Status Menu\n"
            "Jo information chahiye wahi command bhejiye:\n\n"
            "📰 /master news\n"
            "💰 /master xauusd\n"
            "🟢 /master buy\n"
            "🔴 /master sell\n"
            "📱 /master status whatsapp\n"
            "📢 /master status announcement\n"
            "🤖 /master list ai"
        )

    labels = {
        "whatsapp": "WhatsApp Reply Agent",
        "wa": "WhatsApp Reply Agent",
        "announcement": "Announcement Agent",
        "announcements": "Announcement Agent",
        "telegram": "Telegram Reply Agent",
        "blog": "AI Blog Agent",
        "news": "AI Blog / News Agent",
        "signal": "Signal Agent",
        "xauusd": "Signal Agent",
    }

    label = labels.get(requested)
    if label:
        key_map = {
            "whatsapp": "whatsapp_reply_agent",
            "wa": "whatsapp_reply_agent",
            "announcement": "announcement_agent",
            "announcements": "announcement_agent",
            "telegram": "telegram_reply_agent",
            "blog": "ai_blog_agent",
            "news": "ai_blog_agent",
            "signal": "signal_agent",
            "xauusd": "signal_agent",
        }
        try:
            agent = next(
                (
                    item for item in list_ai_agents()
                    if item.get("agent_key") == key_map[requested]
                ),
                None,
            )
        except Exception as exc:
            print(f"[master-ai-status] error={type(exc).__name__}")
            agent = None

        if not agent:
            return f"🤖 {label} status unavailable."

        lines = [
            f"🤖 {label} status",
            f"Enabled: {'ON' if agent.get('is_enabled') else 'OFF'}",
            f"Status: {_safe_word(agent.get('status') or 'UNKNOWN')}",
            f"Queue: {int(agent.get('queue_size') or 0)}",
            f"Last run: {agent.get('last_run_at') or 'Never'}",
        ]
        last_error = str(agent.get("last_error") or "").strip()
        if last_error:
            lines.append(f"Last error: {last_error[:300]}")
        return "\n".join(lines)

    return (
        "🤖 Unknown status option.\n"
        "Use: whatsapp, announcement, telegram, blog, news, signal, ya xauusd."
    )


def _run_started_text(target: str, progress: OrchestrationProgress) -> str:
    text = (
        "🤖 Master AI orchestration accepted.\n"
        f"Task: {target}\n"
        f"Run: #{progress.run_id}\n"
        f"Status: {_safe_word(progress.status)}\n"
        f"Progress: {progress.completed_steps}/{progress.total_steps}"
    )
    if target == "blog":
        url = _latest_blog_public_url()
        if url:
            text += f"\nLatest blog URL: {url}"
        else:
            text += f"\nBlog page: {_public_site_url()}/blog"
    return text


def _unknown_master_text_response() -> str:
    return (
        "🤖 Master AI ready hai.\n"
        "Normal blog command example:\n"
        "xauusd buy or sell today par SEO blog banao\n\n"
        "Direct commands:\n"
        "/master status\n"
        "/master run blog\n"
        "/master list ai"
    )


def _looks_like_signal_text(text: str) -> bool:
    normalized = str(text or "").strip().lower()
    has_side = "buy" in normalized or "sell" in normalized
    has_market = any(
        token in normalized
        for token in ("xauusd", "gold", "btc", "bitcoin", "forex", "signal")
    )
    return has_side and has_market


def _public_site_url() -> str:
    return public_website_base_url()


def _latest_blog_public_url() -> str:
    try:
        from services.content_service import list_content

        rows = list_content(content_type="AI_BLOG", public_only=True, limit=1)
        if not rows:
            rows = list_content(content_type="BLOG", public_only=True, limit=1)
        if not rows:
            return ""
        slug = str(
            rows[0].get("seo_slug")
            or rows[0].get("slug")
            or rows[0].get("id")
            or ""
        ).strip()
        if not slug:
            return ""
        return public_content_url(
            {
                "content_type": rows[0].get("content_type") or "BLOG",
                "slug": slug,
            }
        )
    except Exception:
        return ""


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
