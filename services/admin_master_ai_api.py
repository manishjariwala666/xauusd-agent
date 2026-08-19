"""Protected Master AI endpoints for the secured admin workspace."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Header, Response
from pydantic import BaseModel, Field

from services.admin_auth_api import (
    _bearer_token,
    _require_bff,
    _require_identity,
)
from services.admin_operations_status import get_admin_operations_status
from services.master_ai_chat_service import generate_master_ai_reply


router = APIRouter(
    prefix="/admin/master-ai",
    tags=["admin-master-ai"],
)


class MasterAIChatPayload(BaseModel):
    message: str = Field(min_length=1, max_length=4_000)


def _authenticate(
    authorization: str | None,
    bff_key: str | None,
) -> None:
    _require_bff(bff_key)
    _require_identity(_bearer_token(authorization))


@router.post("/chat")
def master_ai_chat(
    payload: MasterAIChatPayload,
    response: Response,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
) -> dict[str, str]:
    """Use the same verified Master AI backend shared with Telegram."""
    _authenticate(authorization, x_admin_bff_key)
    response.headers["Cache-Control"] = "private, no-store"

    return {
        "reply": generate_master_ai_reply(payload.message),
        "mode": "SHARED_MASTER_AI",
        "execution": "POLICY_GUARDED",
    }


@router.get("/operations")
def master_ai_operations(
    response: Response,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Return the owner-facing read-only launch/operations snapshot."""
    _authenticate(authorization, x_admin_bff_key)
    response.headers["Cache-Control"] = "private, no-store"
    return get_admin_operations_status()
