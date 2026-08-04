"""Protected admin API for persistent agent approval decisions."""

from __future__ import annotations

import logging
from typing import Annotated, Any, Callable

from fastapi import APIRouter, Header, HTTPException, Query, Response
from pydantic import BaseModel, Field

from services.admin_agent_approvals_service import (
    ApprovalConflictError,
    ApprovalNotFoundError,
    approve_agent_request,
    get_agent_approval,
    list_agent_approvals,
    reject_agent_request,
    undo_agent_approval,
)
from services.admin_auth_api import (
    _bearer_token,
    _request_id,
    _require_bff,
    _require_identity,
)
from services.admin_auth_service import AdminIdentity


LOGGER = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/agent-approvals",
    tags=["admin-agent-approvals"],
)


class ApprovalDecisionPayload(BaseModel):
    reason: str = Field(default="", max_length=2_000)


def _identity(
    authorization: str | None,
    bff_secret: str | None,
) -> AdminIdentity:
    _require_bff(bff_secret)
    return _require_identity(_bearer_token(authorization))


def _safe_call(callback: Callable[[], Any]) -> Any:
    try:
        return callback()
    except ApprovalNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ApprovalConflictError as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.exception(
            "Admin agent approval operation failed safely"
        )
        raise HTTPException(
            503,
            "Agent approval service is temporarily unavailable.",
        ) from exc


@router.get("")
def approvals_list(
    response: Response,
    status: str = Query(
        default="all",
        pattern="^(all|pending|approved|rejected|expired)$",
    ),
    agent_key: str = Query(default="", max_length=160),
    limit: int = Query(default=100, ge=1, le=500),
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    _identity(authorization, x_admin_bff_key)
    response.headers["Cache-Control"] = "private, no-store"

    return _safe_call(
        lambda: list_agent_approvals(
            status=status,
            agent_key=agent_key,
            limit=limit,
        )
    )


@router.get("/{approval_id}")
def approval_detail(
    approval_id: int,
    response: Response,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    _identity(authorization, x_admin_bff_key)
    response.headers["Cache-Control"] = "private, no-store"

    return _safe_call(
        lambda: get_agent_approval(approval_id)
    )


@router.post("/{approval_id}/approve")
def approval_approve(
    approval_id: int,
    payload: ApprovalDecisionPayload,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
    x_request_id: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    identity = _identity(
        authorization,
        x_admin_bff_key,
    )

    return _safe_call(
        lambda: approve_agent_request(
            approval_id=approval_id,
            actor_id=identity.user_id,
            request_id=_request_id(x_request_id),
            reason=payload.reason,
        )
    )


@router.post("/{approval_id}/reject")
def approval_reject(
    approval_id: int,
    payload: ApprovalDecisionPayload,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
    x_request_id: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    identity = _identity(
        authorization,
        x_admin_bff_key,
    )

    return _safe_call(
        lambda: reject_agent_request(
            approval_id=approval_id,
            actor_id=identity.user_id,
            request_id=_request_id(x_request_id),
            reason=payload.reason,
        )
    )


@router.post("/{approval_id}/undo")
def approval_undo(
    approval_id: int,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
    x_request_id: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    identity = _identity(
        authorization,
        x_admin_bff_key,
    )

    return _safe_call(
        lambda: undo_agent_approval(
            approval_id=approval_id,
            actor_id=identity.user_id,
            request_id=_request_id(x_request_id),
        )
    )
