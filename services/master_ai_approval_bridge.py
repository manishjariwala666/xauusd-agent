"""Bridge Master AI owner-gated intents into the persistent approval queue.

Creating an approval is not execution. This module never invokes an agent,
sends a message, publishes content, changes infrastructure, or resumes a job.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from services.admin_agent_approvals_service import create_or_refresh_agent_approval
from services.master_ai_capability_matrix import get_agent_capability


@dataclass(frozen=True)
class QueuedApproval:
    queued: bool
    approval_id: int | None = None
    status: str = "UNAVAILABLE"


def queue_master_ai_owner_approval(
    *,
    action: str,
    agent_key: str | None,
    reason: str,
    source: str = "MASTER_AI_CHAT",
) -> QueuedApproval:
    """Persist one new PENDING approval request without executing it."""
    clean_action = str(action or "").strip().lower()
    clean_agent = str(agent_key or "master_ai").strip().lower()
    if not clean_action:
        return QueuedApproval(False)

    capability = get_agent_capability(clean_agent)
    risk = capability.risk.value if capability is not None else "HIGH"
    request_key = f"master-ai:{clean_action}:{uuid4().hex}"

    try:
        row = create_or_refresh_agent_approval(
            request_key=request_key,
            agent_key=clean_agent,
            action_key=clean_action,
            risk_level=risk,
            actor_id=None,
            request_id=f"master-ai-{uuid4().hex}",
            request_payload={
                "source": str(source or "MASTER_AI_CHAT")[:80],
                "reason": str(reason or "Owner approval required.")[:500],
                "execution_requested": False,
            },
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
    except Exception:
        # Approval-table/database availability must never cause an owner-gated
        # action to execute or fall through to an LLM. Fail closed.
        return QueuedApproval(False)

    return QueuedApproval(
        queued=True,
        approval_id=int(row["id"]),
        status=str(row.get("status") or "PENDING").upper(),
    )
