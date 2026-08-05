"""Guarded owner-approved content publishing for VenusRealm."""

from __future__ import annotations

import json
from typing import Any

from services.admin_content_service import (
    get_admin_content,
    transition_content,
)
from services.url_service import public_content_url


APPROVE = "APPROVE"


def validate_publish_approval(
    payload: dict[str, Any],
    content: dict[str, Any],
) -> None:
    """Validate all mandatory approval gates before publishing."""
    content_id = int(payload.get("content_id") or 0)
    actor_id = int(payload.get("actor_id") or 0)
    request_id = str(payload.get("request_id") or "").strip()
    review_decision = str(
        payload.get("master_review_decision") or ""
    ).strip().upper()

    if content_id <= 0:
        raise ValueError("A valid content_id is required.")

    if actor_id <= 0:
        raise PermissionError("A valid owner/admin actor_id is required.")

    if not request_id:
        raise ValueError("A request_id is required for publish audit.")

    if review_decision != APPROVE:
        raise PermissionError(
            "Master AI review decision must be APPROVE."
        )

    if payload.get("owner_approved_publish") is not True:
        raise PermissionError(
            "Explicit owner approval is required before publishing."
        )

    status = str(content.get("status") or "").strip().lower()

    if status == "published":
        raise ValueError("Content is already published.")

    if status != "draft":
        raise PermissionError("Only draft content can be published.")

    if content.get("scheduled_at"):
        raise PermissionError(
            "Scheduled content cannot use immediate publish approval."
        )

    if payload.get("send_telegram") is True:
        raise PermissionError(
            "Publish Approval Agent cannot send Telegram messages."
        )

    if payload.get("send_whatsapp") is True:
        raise PermissionError(
            "Publish Approval Agent cannot send WhatsApp messages."
        )

    if payload.get("delete") is True:
        raise PermissionError(
            "Publish Approval Agent cannot delete content."
        )

    if payload.get("unpublish") is True:
        raise PermissionError(
            "Publish Approval Agent cannot unpublish content."
        )


def run_master_ai_publish_approval_agent(
    payload: dict[str, Any],
) -> str:
    """Publish one approved draft after Master AI and owner approval."""
    content_id = int(payload.get("content_id") or 0)
    actor_id = int(payload.get("actor_id") or 0)
    request_id = str(payload.get("request_id") or "").strip()

    content = get_admin_content(
        kind="posts",
        content_id=content_id,
    )

    validate_publish_approval(payload, content)

    published = transition_content(
        kind="posts",
        content_id=content_id,
        actor_id=actor_id,
        action="publish",
        request_id=request_id,
    )

    slug = str(published.get("slug") or "").strip()
    public_url = public_content_url(
        str(published.get("content_type") or "AI_BLOG"),
        slug,
    )

    result = {
        "status": "PUBLISHED",
        "content_id": int(published["id"]),
        "slug": slug,
        "public_url": public_url,
        "master_review_decision": APPROVE,
        "owner_approval_confirmed": True,
        "telegram_delivery_started": False,
        "whatsapp_delivery_started": False,
        "safe_summary": (
            "Approved draft published successfully. "
            "External distribution requires a separate approved agent."
        ),
    }

    return json.dumps(
        result,
        ensure_ascii=False,
        separators=(",", ":"),
    )
