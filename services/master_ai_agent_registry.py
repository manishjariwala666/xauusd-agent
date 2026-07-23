"""Central agent registry for VenusRealm Master AI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class RegisteredAgent:
    short_name: str
    official_name: str
    agent_key: str
    aliases: tuple[str, ...]
    description: str
    run_action: str | None = None


AGENTS: tuple[RegisteredAgent, ...] = (
    RegisteredAgent(
        short_name="VMA",
        official_name="Venus Master AI",
        agent_key="master_ai",
        aliases=("master ai", "master", "brain", "venus master"),
        description="Controls approved agents, answers admin questions and monitors operations.",
    ),
    RegisteredAgent(
        short_name="VSA",
        official_name="Venus Signal Agent",
        agent_key="signal_agent",
        aliases=("signal", "signal agent", "xauusd", "gold signal"),
        description="Runs the existing Google Sheet based XAUUSD signal workflow.",
        run_action="run_signal_agent",
    ),
    RegisteredAgent(
        short_name="VWRA",
        official_name="Venus WhatsApp Reply Agent",
        agent_key="whatsapp_reply_agent",
        aliases=("whatsapp", "whatsapp agent", "wa reply", "whatsapp reply"),
        description="Processes approved WhatsApp reply workflows.",
        run_action="run_whatsapp_reply_agent",
    ),
    RegisteredAgent(
        short_name="VTRA",
        official_name="Venus Telegram Reply Agent",
        agent_key="telegram_reply_agent",
        aliases=("telegram", "telegram agent", "tg reply", "telegram reply"),
        description="Processes approved Telegram reply workflows.",
        run_action="run_telegram_reply_agent",
    ),
    RegisteredAgent(
        short_name="VBA",
        official_name="Venus Blog Agent",
        agent_key="ai_blog_agent",
        aliases=("blog", "blog agent", "seo", "article", "news content"),
        description="Prepares admin-ready blog and SEO content.",
        run_action="run_blog_agent",
    ),
    RegisteredAgent(
        short_name="VIA",
        official_name="Venus Image Agent",
        agent_key="image_agent",
        aliases=("image", "image agent", "creative", "thumbnail", "photo"),
        description="Prepares admin-ready images and visual content.",
        run_action="run_image_agent",
    ),
    RegisteredAgent(
        short_name="VAA",
        official_name="Venus Announcement Agent",
        agent_key="announcement_agent",
        aliases=("announcement", "announcement agent", "notice"),
        description="Manages announcement preparation and status.",
    ),
    RegisteredAgent(
        short_name="VWHA",
        official_name="Venus Website Health Agent",
        agent_key="website_health_agent",
        aliases=("website health", "site health", "website status", "health agent"),
        description="Checks website and service health.",
    ),
    RegisteredAgent(
        short_name="VDMA",
        official_name="Venus Delivery Monitor Agent",
        agent_key="delivery_monitor_agent",
        aliases=("delivery monitor", "delivery status", "signal delivery"),
        description="Monitors Telegram and WhatsApp delivery state.",
    ),
    RegisteredAgent(
        short_name="VSC",
        official_name="Venus Scheduler Agent",
        agent_key="scheduler_agent",
        aliases=("scheduler", "schedule agent", "cron", "timing"),
        description="Tracks scheduled jobs and due agent runs.",
    ),
    RegisteredAgent(
        short_name="VASA",
        official_name="Venus Admin Support Agent",
        agent_key="admin_support_agent",
        aliases=("admin support", "admin agent", "support agent"),
        description="Supports admin operations and issue summaries.",
    ),
    RegisteredAgent(
        short_name="VRA",
        official_name="Venus Report Agent",
        agent_key="report_agent",
        aliases=("report", "report agent", "system report", "health report"),
        description="Creates periodic system and failure reports.",
    ),
)


def normalize_agent_text(value: str | None) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", " ").split())


def find_agent(value: str | None) -> RegisteredAgent | None:
    requested = normalize_agent_text(value)

    if not requested:
        return None

    for agent in AGENTS:
        candidates = {
            normalize_agent_text(agent.short_name),
            normalize_agent_text(agent.official_name),
            normalize_agent_text(agent.agent_key),
            *(normalize_agent_text(alias) for alias in agent.aliases),
        }

        if requested in candidates:
            return agent

    for agent in AGENTS:
        candidates = (
            agent.short_name,
            agent.official_name,
            agent.agent_key,
            *agent.aliases,
        )

        if any(
            normalize_agent_text(candidate) in requested
            for candidate in candidates
        ):
            return agent

    return None


def list_registered_agents() -> tuple[RegisteredAgent, ...]:
    return AGENTS


def format_agent_directory(
    agents: Iterable[RegisteredAgent] = AGENTS,
) -> str:
    lines = ["🤖 VenusRealm Agent Directory"]

    for agent in agents:
        lines.append(
            f"{agent.short_name} — {agent.official_name}"
        )

    return "\n".join(lines)
