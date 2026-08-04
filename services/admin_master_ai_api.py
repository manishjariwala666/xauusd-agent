"""Protected conversational Master AI endpoint for local admin staging."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, Response
from pydantic import BaseModel, Field

from services.admin_auth_api import (
    _bearer_token,
    _require_bff,
    _require_identity,
)
from services.master_ai_chat_service import generate_master_ai_reply


router = APIRouter(
    prefix="/admin/master-ai",
    tags=["admin-master-ai"],
)


class MasterAIChatPayload(BaseModel):
    message: str = Field(min_length=1, max_length=4_000)


@router.post("/chat")
def master_ai_chat(
    payload: MasterAIChatPayload,
    response: Response,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
) -> dict[str, str]:
    """Return a conversational answer without executing agent actions."""
    _require_bff(x_admin_bff_key)
    _require_identity(_bearer_token(authorization))

    response.headers["Cache-Control"] = "private, no-store"

    return {
        "reply": generate_master_ai_reply(payload.message),
        "mode": "CONVERSATION_ONLY",
        "execution": "LOCKED",
    }
