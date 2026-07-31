"""Protected read-only VenusRealm Agent Dashboard endpoints."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Header, Response

from services.admin_auth_api import (
    _bearer_token,
    _require_bff,
    _require_identity,
)
from services.admin_auth_service import AdminIdentity
from services.ai_agent_service import list_ai_agents
from services.master_ai_agent_registry import (
    get_agent_dashboard_record,
    list_agent_dashboard_records,
    list_registered_agents,
)


router = APIRouter(tags=["agents"])


def _identity(
    authorization: str | None,
    secret: str | None,
) -> AdminIdentity:
    """Require the existing BFF secret and authenticated admin session."""
    _require_bff(secret)
    return _require_identity(_bearer_token(authorization))


@router.get("/admin/agents")
def admin_agent_list(
    response: Response,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Return safe read-only metadata for every registered agent."""
    _identity(authorization, x_admin_bff_key)
    response.headers["Cache-Control"] = "private, no-store"

    items = list_agent_dashboard_records()
    live_by_key = {
        str(item.get("agent_key") or ""): item
        for item in list_ai_agents()
    }

    for item in items:
        live = live_by_key.get(item["agent_key"], {})
        item.update(
            {
                "is_configured": bool(live),
                "is_enabled": live.get("is_enabled"),
                "status": live.get("status") or "NOT_CONFIGURED",
                "last_run_at": live.get("last_run_at"),
                "last_error": str(live.get("last_error") or "")[:500],
                "schedule_minutes": live.get("schedule_minutes"),
                "next_scheduled_run_at": live.get(
                    "next_scheduled_run_at"
                ),
                "success_count": int(live.get("success_count") or 0),
                "failure_count": int(live.get("failure_count") or 0),
                "queue_size": int(live.get("queue_size") or 0),
                "last_duration_ms": live.get("last_duration_ms"),
            }
        )

    return {
        "items": items,
        "count": len(items),
        "read_only": True,
    }


@router.get("/admin/agents/{agent_key}")
def admin_agent_detail(
    agent_key: str,
    response: Response,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Return safe read-only metadata for one registered agent."""
    _identity(authorization, x_admin_bff_key)
    response.headers["Cache-Control"] = "private, no-store"

    normalized = str(agent_key or "").strip().lower()
    agent = next(
        (
            registered
            for registered in list_registered_agents()
            if registered.agent_key == normalized
        ),
        None,
    )

    if agent is None:
        return {
            "item": None,
            "found": False,
            "read_only": True,
        }

    return {
        "item": get_agent_dashboard_record(agent),
        "found": True,
        "read_only": True,
    }
