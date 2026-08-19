"""Protected read-only VenusRealm Agent Dashboard endpoints."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Response

from services.admin_auth_api import _bearer_token, _request_id, _require_bff, _require_identity
from services.admin_auth_service import AdminIdentity, local_admin_preview_enabled
from services.ai_agent_service import list_ai_agents, set_blog_agent_enabled_guarded
from services.agent_brain_generator import generate_brain_preview
from services.master_ai_capability_matrix import CapabilityMode, get_agent_capability
from services.master_ai_agent_registry import get_agent_dashboard_record, list_agent_dashboard_records, list_registered_agents
from services.worker_agent_adapter import ORCHESTRATION_NATIVE_AGENT_KEYS


router = APIRouter(tags=["agents"])

SCHEDULED_WORKER_AGENT_KEYS = frozenset({
    "ai_blog_agent",
    "telegram_reply_agent",
    "whatsapp_reply_agent",
    "signal_agent",
    "announcement_agent",
    "seo_agent",
    "image_agent",
})


def _identity(authorization: str | None, secret: str | None) -> AdminIdentity:
    _require_bff(secret)
    return _require_identity(_bearer_token(authorization))


def _embedded_status(item: dict[str, Any], capability: Any | None) -> str:
    if not item.get("brain_configured") or capability is None:
        return "NOT_CONFIGURED"
    if capability.mode == CapabilityMode.READ:
        return "READY_READ_ONLY"
    if capability.mode == CapabilityMode.APPROVAL:
        return "APPROVAL_GATED"
    if capability.mode == CapabilityMode.BLOCKED:
        return "BLOCKED"
    return "READY"


def _load_live_agents() -> list[dict[str, Any]]:
    try:
        return list_ai_agents()
    except Exception:
        if not local_admin_preview_enabled():
            raise
        return []


def _decorate_agent_item(
    item: dict[str, Any],
    *,
    live_by_key: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    key = str(item.get("agent_key") or "")
    live = live_by_key.get(key, {})
    capability = get_agent_capability(key)

    if key in SCHEDULED_WORKER_AGENT_KEYS:
        runtime_kind = "SCHEDULED_WORKER"
        is_configured = bool(live)
        is_enabled = live.get("is_enabled")
        status = str(live.get("status") or "NOT_CONFIGURED")
    elif key in ORCHESTRATION_NATIVE_AGENT_KEYS:
        # These runners are intentionally Master-AI-only unless a future DB row
        # is explicitly created. If a DB row exists, its enabled state wins.
        runtime_kind = "MASTER_AI_NATIVE"
        is_configured = bool(item.get("brain_configured") and capability is not None)
        is_enabled = live.get("is_enabled") if live else True
        status = (
            str(live.get("status") or "NOT_CONFIGURED")
            if live
            else _embedded_status(item, capability)
        )
    else:
        runtime_kind = "EMBEDDED"
        is_configured = bool(item.get("brain_configured") and capability is not None)
        is_enabled = True
        status = _embedded_status(item, capability)

    decorated = dict(item)
    decorated.update({
        "runtime_kind": runtime_kind,
        "worker_configured": bool(live),
        "capability_mode": capability.mode.value if capability is not None else "BLOCKED",
        "capability_risk": capability.risk.value if capability is not None else "CRITICAL",
        "owner_approval_required": capability.owner_approval_required if capability is not None else True,
        "capability_allowed_actions": list(capability.allowed_actions) if capability is not None else [],
        "capability_blocked_actions": list(capability.blocked_actions) if capability is not None else ["No capability policy configured"],
        "capability_dependencies": list(capability.dependencies) if capability is not None else [],
        "is_configured": is_configured,
        "is_enabled": is_enabled,
        "status": status,
        "last_run_at": live.get("last_run_at"),
        "last_error": str(live.get("last_error") or "")[:500],
        "schedule_minutes": live.get("schedule_minutes"),
        "next_scheduled_run_at": live.get("next_scheduled_run_at"),
        "success_count": int(live.get("success_count") or 0),
        "failure_count": int(live.get("failure_count") or 0),
        "queue_size": int(live.get("queue_size") or 0),
        "last_duration_ms": live.get("last_duration_ms"),
    })
    return decorated


@router.get("/admin/agents")
def admin_agent_list(
    response: Response,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Return truthful brain, capability, and runtime metadata for every agent."""
    _identity(authorization, x_admin_bff_key)
    response.headers["Cache-Control"] = "private, no-store"
    live_by_key = {str(row.get("agent_key") or ""): row for row in _load_live_agents()}
    items = [
        _decorate_agent_item(item, live_by_key=live_by_key)
        for item in list_agent_dashboard_records()
    ]
    return {"items": items, "count": len(items), "read_only": True}


@router.post("/admin/agents/builder/preview")
def admin_agent_builder_preview(
    payload: dict[str, Any],
    response: Response,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    _identity(authorization, x_admin_bff_key)
    response.headers["Cache-Control"] = "private, no-store"
    try:
        preview = generate_brain_preview(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Agent brain preview service is temporarily unavailable.") from exc
    return {
        "preview": preview,
        "preview_only": True,
        "execution_enabled": False,
        "registry_written": False,
        "runner_written": False,
        "files_generated": False,
    }


@router.get("/admin/agents/{agent_key}")
def admin_agent_detail(
    agent_key: str,
    response: Response,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Return the same truthful runtime/capability state as the list endpoint."""
    _identity(authorization, x_admin_bff_key)
    response.headers["Cache-Control"] = "private, no-store"
    normalized = str(agent_key or "").strip().lower()
    agent = next((registered for registered in list_registered_agents() if registered.agent_key == normalized), None)
    if agent is None:
        return {"item": None, "found": False, "read_only": True}
    live_by_key = {str(row.get("agent_key") or ""): row for row in _load_live_agents()}
    item = _decorate_agent_item(get_agent_dashboard_record(agent), live_by_key=live_by_key)
    return {"item": item, "found": True, "read_only": True}


@router.post("/admin/agents/{agent_key}/enabled")
def admin_agent_enabled_update(
    agent_key: str,
    payload: dict[str, bool],
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
    x_request_id: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Guarded enable/disable control for AI Blog Agent only."""
    identity = _identity(authorization, x_admin_bff_key)
    if "enabled" not in payload:
        raise HTTPException(status_code=422, detail="Enabled state is required.")
    try:
        result = set_blog_agent_enabled_guarded(
            agent_key=agent_key,
            enabled=bool(payload["enabled"]),
            actor_id=identity.user_id,
            request_id=_request_id(x_request_id),
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Agent control service is temporarily unavailable.") from exc
    return {
        **result,
        "message": "AI Blog Agent enabled state updated." if result["changed"] else "AI Blog Agent was already in the requested state.",
    }
