"""Read-only operational snapshot for the protected VenusRealm admin panel."""

from __future__ import annotations

import re
from typing import Any

from loguru import logger
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from core.database import session_scope
from services.ai_agent_service import list_ai_agents
from services.captain_shadow_audit import latest_captain_shadow_audit
from services.master_orchestrator import list_orchestration_runs


_MISSING_TABLE_SQLSTATE = "42P01"


def _missing_table(exc: BaseException) -> bool:
    original = getattr(exc, "orig", None)
    return getattr(original, "sqlstate", None) == _MISSING_TABLE_SQLSTATE


def _word_count(body: object) -> int:
    text_value = re.sub(r"<[^>]+>", " ", str(body or ""))
    return len(re.findall(r"\b[\w'-]+\b", text_value))


def _agent_summary() -> dict[str, Any]:
    try:
        rows = list_ai_agents()
    except Exception as exc:
        logger.warning(
            "Admin operations agent summary unavailable: {}",
            exc.__class__.__name__,
        )
        return {"available": False, "count": 0, "enabled": 0, "errors": 0}

    return {
        "available": True,
        "count": len(rows),
        "enabled": sum(1 for row in rows if row.get("is_enabled")),
        "errors": sum(
            1
            for row in rows
            if str(row.get("status") or "").upper() == "ERROR"
            or bool(row.get("last_error"))
        ),
    }


def _run_summary() -> dict[str, Any]:
    try:
        rows = list_orchestration_runs(limit=10)
    except Exception as exc:
        if isinstance(exc, ProgrammingError) and _missing_table(exc):
            return {"available": False, "reason": "orchestration migration unavailable", "items": []}
        logger.warning(
            "Admin operations run summary unavailable: {}",
            exc.__class__.__name__,
        )
        return {"available": False, "reason": "runtime unavailable", "items": []}

    items = [
        {
            "run_id": row.get("run_id"),
            "title": row.get("title"),
            "task_type": row.get("task_type"),
            "status": row.get("status"),
            "completed_steps": int(row.get("completed_steps") or 0),
            "total_steps": int(row.get("total_steps") or 0),
            "failed_steps": int(row.get("failed_steps") or 0),
            "safe_error": str(row.get("safe_error") or "")[:500] or None,
        }
        for row in rows
    ]
    return {"available": True, "items": items}


def _content_summary() -> dict[str, Any]:
    try:
        with session_scope() as session:
            rows = (
                session.execute(
                    text(
                        """
                        SELECT id, title, body, image_url, is_published,
                               published_at, updated_at
                        FROM public.content_items
                        WHERE content_type = 'AI_BLOG'
                        ORDER BY updated_at DESC, id DESC
                        LIMIT 10
                        """
                    )
                )
                .mappings()
                .all()
            )
    except Exception as exc:
        if isinstance(exc, ProgrammingError) and _missing_table(exc):
            return {"available": False, "reason": "content table unavailable", "items": []}
        logger.warning(
            "Admin operations content summary unavailable: {}",
            exc.__class__.__name__,
        )
        return {"available": False, "reason": "runtime unavailable", "items": []}

    items = [
        {
            "id": row.get("id"),
            "title": str(row.get("title") or "")[:240],
            "status": "PUBLISHED" if row.get("is_published") else "DRAFT",
            "featured_image": str(row.get("image_url") or "") or None,
            "word_count": _word_count(row.get("body")),
            "published_at": row.get("published_at"),
            "updated_at": row.get("updated_at"),
        }
        for row in rows
    ]
    return {
        "available": True,
        "drafts": sum(1 for item in items if item["status"] == "DRAFT"),
        "published": sum(1 for item in items if item["status"] == "PUBLISHED"),
        "items": items,
        "automatic_publish": False,
    }


def _delivery_summary() -> dict[str, Any]:
    try:
        with session_scope() as session:
            rows = (
                session.execute(
                    text(
                        """
                        SELECT d.signal_id, d.channel, d.recipient_hash,
                               d.attempts, d.claimed_at, d.sent_at,
                               d.error_category, d.updated_at
                        FROM public.signal_channel_deliveries d
                        ORDER BY d.updated_at DESC, d.id DESC
                        LIMIT 100
                        """
                    )
                )
                .mappings()
                .all()
            )
    except Exception as exc:
        if isinstance(exc, ProgrammingError) and _missing_table(exc):
            return {
                "available": False,
                "reason": "durable delivery migration unavailable",
                "max_attempts": 3,
                "stale_claim_minutes": 5,
                "channels": {},
                "failed_recipients": [],
            }
        logger.warning(
            "Admin operations delivery summary unavailable: {}",
            exc.__class__.__name__,
        )
        return {
            "available": False,
            "reason": "runtime unavailable",
            "max_attempts": 3,
            "stale_claim_minutes": 5,
            "channels": {},
            "failed_recipients": [],
        }

    channels: dict[str, dict[str, int]] = {
        "telegram": {"sent": 0, "pending": 0, "failed": 0},
        "whatsapp": {"sent": 0, "pending": 0, "failed": 0},
    }
    failed_recipients: list[dict[str, Any]] = []
    for row in rows:
        channel = str(row.get("channel") or "").lower()
        if channel not in channels:
            continue
        if row.get("sent_at"):
            channels[channel]["sent"] += 1
        else:
            channels[channel]["pending"] += 1
            if row.get("error_category"):
                channels[channel]["failed"] += 1
                if len(failed_recipients) < 20:
                    failed_recipients.append(
                        {
                            "signal_id": row.get("signal_id"),
                            "channel": channel,
                            "recipient": str(row.get("recipient_hash") or "")[:12],
                            "attempts": int(row.get("attempts") or 0),
                            "error_category": str(row.get("error_category") or "")[:120],
                        }
                    )

    return {
        "available": True,
        "max_attempts": 3,
        "stale_claim_minutes": 5,
        "channels": channels,
        "failed_recipients": failed_recipients,
        "duplicate_prevention": "per signal/channel/recipient ledger",
    }


def _captain_summary() -> dict[str, Any]:
    try:
        row = latest_captain_shadow_audit()
    except Exception as exc:
        logger.warning(
            "Admin operations Captain audit unavailable: {}",
            exc.__class__.__name__,
        )
        return {"available": False, "reason": "runtime unavailable"}

    if not row:
        return {
            "available": False,
            "reason": "captain_shadow_audits migration or verified audit unavailable",
        }

    return {
        "available": True,
        "correlation_id": row.get("correlation_id"),
        "recorded_at": row.get("created_at"),
        "source_interface": row.get("source_interface"),
        "signal_id": row.get("signal_id"),
        "signal_date": row.get("signal_date"),
        "market_source": row.get("market_source"),
        "cmp": row.get("live_cmp"),
        "high": row.get("day_high"),
        "low": row.get("day_low"),
        "buy_base": row.get("buy_base"),
        "sell_base": row.get("sell_base"),
        "captain_decision": row.get("captain_decision"),
        "captain_direction": row.get("captain_direction"),
        "captain_confidence": row.get("captain_confidence"),
        "shadow_status": row.get("shadow_status"),
        "shadow_reason": row.get("shadow_reason"),
        "telegram_delivered": row.get("telegram_delivered"),
        "whatsapp_delivered": row.get("whatsapp_delivered"),
        "master_ai_summary": row.get("master_ai_summary"),
    }


def get_admin_operations_status() -> dict[str, Any]:
    """Return one fail-safe read-only status payload for owner operations."""
    return {
        "read_only": True,
        "master_ai": {
            "shared_backend": "generate_master_ai_reply",
            "interfaces": ["ADMIN", "TELEGRAM"],
            "execution_mode": "POLICY_GUARDED",
            "agents": _agent_summary(),
            "runs": _run_summary(),
        },
        "signal": _captain_summary(),
        "content": _content_summary(),
        "delivery": _delivery_summary(),
        "safety": {
            "publishing": "OWNER_APPROVAL_REQUIRED",
            "production_deployment": "OWNER_APPROVAL_REQUIRED",
            "dns": "LOCKED_UNLESS_OWNER_APPROVED",
            "database_migration": "EXPLICIT_OWNER_APPROVAL_REQUIRED",
            "trade_execution": "FORBIDDEN",
            "automatic_content_publish": False,
        },
    }
