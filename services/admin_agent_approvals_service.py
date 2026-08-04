"""Persistent approval workflow for VenusRealm agents."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any

from sqlalchemy import text

from core.database import session_scope


VALID_STATUSES = {
    "PENDING",
    "APPROVED",
    "REJECTED",
    "EXPIRED",
}

VALID_RISKS = {
    "READ_ONLY",
    "LOW",
    "HIGH",
    "CRITICAL",
    "UNKNOWN",
}


class ApprovalNotFoundError(ValueError):
    """Requested approval does not exist."""


class ApprovalConflictError(ValueError):
    """Approval state transition is no longer valid."""


def list_agent_approvals(
    *,
    status: str = "all",
    agent_key: str = "",
    limit: int = 100,
) -> dict[str, Any]:
    normalized_status = str(status or "all").strip().upper()
    normalized_agent = str(agent_key or "").strip()
    bounded_limit = max(1, min(500, int(limit)))

    clauses = ["1 = 1"]
    parameters: dict[str, Any] = {
        "limit": bounded_limit,
    }

    if normalized_status != "ALL":
        if normalized_status not in VALID_STATUSES:
            raise ValueError("Unsupported approval status.")
        clauses.append("r.status = :status")
        parameters["status"] = normalized_status

    if normalized_agent:
        clauses.append("r.agent_key = :agent_key")
        parameters["agent_key"] = normalized_agent

    where_clause = " AND ".join(clauses)

    with session_scope() as session:
        rows = session.execute(
            text(
                f"""
                SELECT
                    r.id,
                    r.request_key,
                    r.agent_key,
                    r.action_key,
                    r.risk_level,
                    r.status,
                    r.request_payload,
                    r.requested_by,
                    r.requested_at,
                    r.expires_at,
                    r.decided_by,
                    r.decided_at,
                    r.decision_reason,
                    r.version,
                    r.created_at,
                    r.updated_at
                FROM public.agent_approval_requests r
                WHERE {where_clause}
                ORDER BY
                    CASE r.status
                        WHEN 'PENDING' THEN 0
                        WHEN 'APPROVED' THEN 1
                        WHEN 'REJECTED' THEN 2
                        ELSE 3
                    END,
                    r.created_at DESC,
                    r.id DESC
                LIMIT :limit
                """
            ),
            parameters,
        ).mappings().all()

    return {
        "items": [dict(row) for row in rows],
        "count": len(rows),
    }


def get_agent_approval(approval_id: int) -> dict[str, Any]:
    with session_scope() as session:
        row = session.execute(
            text(
                """
                SELECT
                    r.id,
                    r.request_key,
                    r.agent_key,
                    r.action_key,
                    r.risk_level,
                    r.status,
                    r.request_payload,
                    r.requested_by,
                    r.requested_at,
                    r.expires_at,
                    r.decided_by,
                    r.decided_at,
                    r.decision_reason,
                    r.version,
                    r.created_at,
                    r.updated_at
                FROM public.agent_approval_requests r
                WHERE r.id = :approval_id
                """
            ),
            {"approval_id": int(approval_id)},
        ).mappings().first()

    if not row:
        raise ApprovalNotFoundError(
            "Agent approval request was not found."
        )

    return dict(row)


def create_or_refresh_agent_approval(
    *,
    request_key: str,
    agent_key: str,
    action_key: str,
    risk_level: str,
    actor_id: int | None,
    request_id: str,
    request_payload: dict[str, Any] | None = None,
    expires_at: datetime | None = None,
) -> dict[str, Any]:
    normalized_request_key = str(request_key or "").strip()
    normalized_agent_key = str(agent_key or "").strip()
    normalized_action_key = str(action_key or "").strip()
    normalized_risk = str(risk_level or "UNKNOWN").strip().upper()

    if not normalized_request_key:
        raise ValueError("Approval request key is required.")
    if not normalized_agent_key:
        raise ValueError("Agent key is required.")
    if not normalized_action_key:
        raise ValueError("Action key is required.")
    if normalized_risk not in VALID_RISKS:
        raise ValueError("Unsupported approval risk level.")

    payload_json = json.dumps(request_payload or {})

    with session_scope() as session:
        row = session.execute(
            text(
                """
                INSERT INTO public.agent_approval_requests (
                    request_key,
                    agent_key,
                    action_key,
                    risk_level,
                    status,
                    request_payload,
                    requested_by,
                    requested_at,
                    expires_at,
                    decided_by,
                    decided_at,
                    decision_reason,
                    version,
                    created_at,
                    updated_at
                ) VALUES (
                    :request_key,
                    :agent_key,
                    :action_key,
                    :risk_level,
                    'PENDING',
                    CAST(:request_payload AS JSONB),
                    :actor_id,
                    NOW(),
                    :expires_at,
                    NULL,
                    NULL,
                    '',
                    1,
                    NOW(),
                    NOW()
                )
                ON CONFLICT (request_key)
                DO UPDATE SET
                    request_payload = EXCLUDED.request_payload,
                    expires_at = EXCLUDED.expires_at,
                    updated_at = NOW()
                RETURNING *
                """
            ),
            {
                "request_key": normalized_request_key,
                "agent_key": normalized_agent_key,
                "action_key": normalized_action_key,
                "risk_level": normalized_risk,
                "request_payload": payload_json,
                "actor_id": actor_id,
                "expires_at": expires_at,
            },
        ).mappings().one()

        _audit(
            session=session,
            approval_id=int(row["id"]),
            event_type="REQUESTED",
            previous_status=None,
            next_status=str(row["status"]),
            actor_id=actor_id,
            request_id=request_id,
            safe_details={
                "agent_key": normalized_agent_key,
                "action_key": normalized_action_key,
            },
        )

    return dict(row)


def approve_agent_request(
    *,
    approval_id: int,
    actor_id: int,
    request_id: str,
    reason: str = "",
) -> dict[str, Any]:
    return _decide(
        approval_id=approval_id,
        actor_id=actor_id,
        request_id=request_id,
        next_status="APPROVED",
        reason=reason,
    )


def reject_agent_request(
    *,
    approval_id: int,
    actor_id: int,
    request_id: str,
    reason: str = "",
) -> dict[str, Any]:
    return _decide(
        approval_id=approval_id,
        actor_id=actor_id,
        request_id=request_id,
        next_status="REJECTED",
        reason=reason,
    )


def undo_agent_approval(
    *,
    approval_id: int,
    actor_id: int,
    request_id: str,
) -> dict[str, Any]:
    with session_scope() as session:
        current = session.execute(
            text(
                """
                SELECT id, status, version
                FROM public.agent_approval_requests
                WHERE id = :approval_id
                FOR UPDATE
                """
            ),
            {"approval_id": int(approval_id)},
        ).mappings().first()

        if not current:
            raise ApprovalNotFoundError(
                "Agent approval request was not found."
            )

        previous_status = str(current["status"])

        if previous_status not in {"APPROVED", "REJECTED"}:
            raise ApprovalConflictError(
                "Only approved or rejected requests can be undone."
            )

        row = session.execute(
            text(
                """
                UPDATE public.agent_approval_requests
                SET status = 'PENDING',
                    decided_by = NULL,
                    decided_at = NULL,
                    decision_reason = '',
                    version = version + 1,
                    updated_at = NOW()
                WHERE id = :approval_id
                  AND version = :version
                RETURNING *
                """
            ),
            {
                "approval_id": int(approval_id),
                "version": int(current["version"]),
            },
        ).mappings().first()

        if not row:
            raise ApprovalConflictError(
                "Approval changed before undo could complete."
            )

        _audit(
            session=session,
            approval_id=int(approval_id),
            event_type="UNDONE",
            previous_status=previous_status,
            next_status="PENDING",
            actor_id=actor_id,
            request_id=request_id,
            safe_details={},
        )

    return dict(row)


def _decide(
    *,
    approval_id: int,
    actor_id: int,
    request_id: str,
    next_status: str,
    reason: str,
) -> dict[str, Any]:
    if next_status not in {"APPROVED", "REJECTED"}:
        raise ValueError("Unsupported approval decision.")

    with session_scope() as session:
        current = session.execute(
            text(
                """
                SELECT id, status, version, expires_at
                FROM public.agent_approval_requests
                WHERE id = :approval_id
                FOR UPDATE
                """
            ),
            {"approval_id": int(approval_id)},
        ).mappings().first()

        if not current:
            raise ApprovalNotFoundError(
                "Agent approval request was not found."
            )

        if str(current["status"]) != "PENDING":
            raise ApprovalConflictError(
                "Approval request is no longer pending."
            )

        expires_at = current["expires_at"]
        if (
            expires_at is not None
            and expires_at <= datetime.now(timezone.utc)
        ):
            raise ApprovalConflictError(
                "Approval request has expired."
            )

        row = session.execute(
            text(
                """
                UPDATE public.agent_approval_requests
                SET status = :next_status,
                    decided_by = :actor_id,
                    decided_at = NOW(),
                    decision_reason = :reason,
                    version = version + 1,
                    updated_at = NOW()
                WHERE id = :approval_id
                  AND version = :version
                  AND status = 'PENDING'
                RETURNING *
                """
            ),
            {
                "approval_id": int(approval_id),
                "actor_id": int(actor_id),
                "next_status": next_status,
                "reason": str(reason or "").strip()[:2_000],
                "version": int(current["version"]),
            },
        ).mappings().first()

        if not row:
            raise ApprovalConflictError(
                "Approval changed before decision completed."
            )

        _audit(
            session=session,
            approval_id=int(approval_id),
            event_type=next_status,
            previous_status="PENDING",
            next_status=next_status,
            actor_id=actor_id,
            request_id=request_id,
            safe_details={
                "reason_present": bool(str(reason or "").strip()),
            },
        )

    return dict(row)


def _audit(
    *,
    session: Any,
    approval_id: int,
    event_type: str,
    previous_status: str | None,
    next_status: str | None,
    actor_id: int | None,
    request_id: str,
    safe_details: dict[str, Any],
) -> None:
    session.execute(
        text(
            """
            INSERT INTO public.agent_approval_audit_events (
                approval_id,
                event_type,
                previous_status,
                next_status,
                actor_id,
                request_id,
                safe_details
            ) VALUES (
                :approval_id,
                :event_type,
                :previous_status,
                :next_status,
                :actor_id,
                :request_id,
                CAST(:safe_details AS JSONB)
            )
            """
        ),
        {
            "approval_id": int(approval_id),
            "event_type": event_type,
            "previous_status": previous_status,
            "next_status": next_status,
            "actor_id": actor_id,
            "request_id": str(request_id or ""),
            "safe_details": json.dumps(safe_details),
        },
    )
