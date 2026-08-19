"""Central agent registry for VenusRealm Master AI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from services.agent_brain_registry import get_agent_brain


@dataclass(frozen=True)
class RegisteredAgent:
    short_name: str
    official_name: str
    agent_key: str
    aliases: tuple[str, ...]
    description: str
    run_action: str | None = None


AGENTS: tuple[RegisteredAgent, ...] = (
    RegisteredAgent("VMA", "Venus Master AI", "master_ai", ("master ai", "master", "brain", "venus master"), "Controls approved agents, answers admin questions and monitors operations."),
    RegisteredAgent("VSA", "Venus Signal Agent", "signal_agent", ("signal", "signal agent", "xauusd", "gold signal"), "Runs the existing Google Sheet based XAUUSD signal workflow.", "run_signal_agent"),
    RegisteredAgent("VWRA", "Venus WhatsApp Reply Agent", "whatsapp_reply_agent", ("whatsapp", "whatsapp agent", "wa reply", "whatsapp reply"), "Processes approved WhatsApp reply workflows.", "run_whatsapp_reply_agent"),
    RegisteredAgent("VTRA", "Venus Telegram Reply Agent", "telegram_reply_agent", ("telegram", "telegram agent", "tg reply", "telegram reply"), "Processes approved Telegram reply workflows.", "run_telegram_reply_agent"),
    RegisteredAgent("VBA", "Venus Blog Agent", "ai_blog_agent", ("blog", "blog agent", "article", "news content"), "Prepares admin-ready blog and SEO content.", "run_blog_agent"),
    RegisteredAgent("VMDA", "Venus Market Data Agent", "market_data_agent", ("market data", "live price", "xauusd price", "google finance price", "gold price"), "Validates current XAUUSD market snapshots from Google Finance sheets or approved broker feeds.", "run_market_data_agent"),
    RegisteredAgent("VCSA", "Venus Customer Support Agent", "customer_support_agent", ("customer support", "website support agent", "client guidance agent", "lead support agent"), "Guides website visitors, qualifies new-client leads and prepares safe support escalation.", "run_customer_support_agent"),
    RegisteredAgent("VMSA", "Venus Marketing Strategy Agent", "marketing_strategy_agent", ("marketing strategist", "marketing strategy agent", "campaign planner", "marketing team leader"), "Creates approval-ready marketing campaign plans for published VenusRealm content.", "run_marketing_strategy_agent"),
    RegisteredAgent("VSMA", "Venus Social Media Agent", "social_media_agent", ("social media", "social media agent", "social content", "social post drafts", "linkedin content", "instagram content", "facebook content", "x content"), "Prepares platform-specific social media drafts for approved published VenusRealm content.", "run_social_media_agent"),
    RegisteredAgent("VMPAA", "Venus Master Publish Approval Agent", "master_publish_approval_agent", ("publish approval", "publish approval agent", "owner approved publish", "master publish agent"), "Publishes one reviewed draft only after explicit owner approval.", "run_master_ai_publish_approval_agent"),
    RegisteredAgent("VMCRA", "Venus Master Content Review Agent", "master_content_review_agent", ("master content review", "content review agent", "publish review", "master ai review"), "Performs read-only publish-readiness review for structured CMS drafts.", "run_master_ai_content_review_agent"),
    RegisteredAgent("VCEA", "Venus CMS Editor Agent", "cms_editor_agent", ("cms editor", "cms editor agent", "content editor agent", "studio v2 agent"), "Converts approved article content into structured Studio V2 drafts.", "run_cms_editor_agent"),
    RegisteredAgent("VIA", "Venus Image Agent", "image_agent", ("image", "image agent", "creative", "thumbnail", "photo"), "Prepares admin-ready images and visual content.", "run_image_agent"),
    RegisteredAgent("VAA", "Venus Announcement Agent", "announcement_agent", ("announcement", "announcement agent", "notice"), "Manages approved announcement delivery and status.", "run_announcement_agent"),
    RegisteredAgent("VSEO", "Venus SEO Agent", "seo_agent", ("seo agent", "seo audit", "seo metadata", "content seo"), "Audits published content and can persist SEO metadata improvements only through owner-approved execution.", "run_seo_agent"),
    RegisteredAgent("VMAI", "Venus Macro AI", "macro_ai_agent", ("macro ai", "macro agent", "market macro", "gold macro intelligence"), "Provides read-only XAUUSD macro bias using approved market snapshots, correlations and deterministic scoring."),
    RegisteredAgent("VECA", "Venus Economic Calendar AI", "economic_calendar_ai_agent", ("economic calendar", "calendar ai", "news lock", "usa canada news", "high impact news"), "Classifies approved USA and Canada economic events, calculates event surprise and provides read-only news-lock guidance."),
    RegisteredAgent("VWHA", "Venus Website Health Agent", "website_health_agent", ("website health", "site health", "website status", "health agent"), "Checks website and service health."),
    RegisteredAgent("VDMA", "Venus Delivery Monitor Agent", "delivery_monitor_agent", ("delivery monitor", "delivery status", "signal delivery"), "Monitors Telegram and WhatsApp delivery state."),
    RegisteredAgent("VSC", "Venus Scheduler Agent", "scheduler_agent", ("scheduler", "schedule agent", "cron", "timing"), "Tracks scheduled jobs and due agent runs."),
    RegisteredAgent("VASA", "Venus Admin Support Agent", "admin_support_agent", ("admin support", "admin agent", "support agent"), "Supports admin operations and issue summaries."),
    RegisteredAgent("VRA", "Venus Report Agent", "report_agent", ("report", "report agent", "system report", "health report"), "Creates periodic system and failure reports."),
)


def normalize_agent_text(value: str | None) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", " ").split())


def find_agent(value: str | None) -> RegisteredAgent | None:
    requested = normalize_agent_text(value)
    if not requested:
        return None
    for agent in AGENTS:
        candidates = {
            normalize_agent_text(agent.short_name), normalize_agent_text(agent.official_name),
            normalize_agent_text(agent.agent_key), *(normalize_agent_text(alias) for alias in agent.aliases),
        }
        if requested in candidates:
            return agent
    for agent in AGENTS:
        candidates = (agent.short_name, agent.official_name, agent.agent_key, *agent.aliases)
        if any(normalize_agent_text(candidate) in requested for candidate in candidates):
            return agent
    return None


def list_registered_agents() -> tuple[RegisteredAgent, ...]:
    return AGENTS


def format_agent_directory(agents: Iterable[RegisteredAgent] = AGENTS) -> str:
    lines = ["🤖 VenusRealm Agent Directory"]
    for agent in agents:
        lines.append(f"{agent.short_name} — {agent.official_name}")
    return "\n".join(lines)


def get_agent_dashboard_record(agent: RegisteredAgent) -> dict[str, Any]:
    brain = get_agent_brain(agent.agent_key)
    record: dict[str, Any] = {
        "agent_key": agent.agent_key, "short_name": agent.short_name,
        "official_name": agent.official_name, "description": agent.description,
        "aliases": list(agent.aliases), "run_action": agent.run_action,
        "brain_configured": brain is not None, "can_toggle": agent.agent_key == "ai_blog_agent",
    }
    if brain is None:
        record.update({"purpose": agent.description, "default_risk": "UNKNOWN", "automatic_actions": [], "approval_required_actions": [], "forbidden_actions": [], "output_schema": []})
        return record
    record.update({
        "purpose": brain.purpose, "default_risk": brain.default_risk.value,
        "automatic_actions": list(brain.automatic_actions),
        "approval_required_actions": list(brain.approval_required_actions),
        "forbidden_actions": list(brain.forbidden_actions),
        "output_schema": list(brain.output_schema),
    })
    return record


def list_agent_dashboard_records() -> list[dict[str, Any]]:
    return [get_agent_dashboard_record(agent) for agent in list_registered_agents()]
