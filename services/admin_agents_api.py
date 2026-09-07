"""Protected admin API routes for AI agent status and toggles."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Response
from pydantic import BaseModel

from services.admin_auth_service import (
    AdminAccessForbidden,
    AdminAuthUnavailable,
    AdminIdentity,
    AdminSessionInvalid,
    validate_admin_session,
    verify_bff_secret,
)
from services.ai_agent_service import (
    list_agent_runs,
    list_ai_agents,
    set_ai_agent_enabled,
)

router = APIRouter(prefix="/admin/agents", tags=["admin-agents"])


class AdminAgentsResponse(BaseModel):
    agents: list[dict[str, object]]
    runs: list[dict[str, object]]


def _bearer_token(authorization: str | None) -> str:
    scheme, _, token = str(authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(401, "Admin authentication is required.")
    return token.strip()


def _require_bff(provided: str | None) -> None:
    try:
        verify_bff_secret(provided)
    except AdminAuthUnavailable as exc:
        raise HTTPException(503, "Admin authentication is unavailable.") from exc
    except AdminAccessForbidden as exc:
        raise HTTPException(403, "Admin BFF authorization failed.") from exc


def _require_identity(token: str) -> AdminIdentity:
    try:
        return validate_admin_session(token)
    except AdminAccessForbidden as exc:
        raise HTTPException(403, "Administrator access is forbidden.") from exc
    except AdminSessionInvalid as exc:
        raise HTTPException(401, "Admin session is invalid or expired.") from exc


@router.get("", response_model=AdminAgentsResponse)
def list_admin_agents(
    response: Response,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
) -> AdminAgentsResponse:
    """Return the current agent status and recent execution runs."""
    _require_bff(x_admin_bff_key)
    _require_identity(_bearer_token(authorization))
    response.headers["Cache-Control"] = "private, no-store"
    return AdminAgentsResponse(
        agents=list_ai_agents(),
        runs=list_agent_runs(limit=10),
    )


@router.get("/runs", response_model=list[dict[str, object]])
def list_admin_agent_runs(
    response: Response,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
) -> list[dict[str, object]]:
    """Return the most recent agent execution rows."""
    _require_bff(x_admin_bff_key)
    _require_identity(_bearer_token(authorization))
    response.headers["Cache-Control"] = "private, no-store"
    return list_agent_runs(limit=10)


@router.post("/{agent_key}/enable", response_model=dict[str, object])
def enable_admin_agent(
    agent_key: str,
    response: Response,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
) -> dict[str, object]:
    """Enable an existing AI agent."""
    _require_bff(x_admin_bff_key)
    _require_identity(_bearer_token(authorization))
    try:
        set_ai_agent_enabled(agent_key, True)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    response.headers["Cache-Control"] = "private, no-store"
    return {"agent_key": agent_key, "enabled": True}


@router.post("/{agent_key}/disable", response_model=dict[str, object])
def disable_admin_agent(
    agent_key: str,
    response: Response,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
) -> dict[str, object]:
    """Disable an existing AI agent."""
    _require_bff(x_admin_bff_key)
    _require_identity(_bearer_token(authorization))
    try:
        set_ai_agent_enabled(agent_key, False)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    response.headers["Cache-Control"] = "private, no-store"
    return {"agent_key": agent_key, "enabled": False}
