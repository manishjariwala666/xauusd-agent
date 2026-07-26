"""PostgreSQL adapter for WhatsApp standing authorization.

The adapter assumes the additive schema documented by the launch report. It
does not create tables or run migrations. Callers must fail closed when that
schema or database configuration is unavailable.
"""

from __future__ import annotations

from datetime import datetime
import json
from typing import Any

from sqlalchemy import text

from core.database import session_scope
from services.whatsapp_standing_authorization import (
    AuthorizationStatus,
    AutomationAuditEvent,
    ClientAutomationState,
    DeliveryAttemptState,
    FailedDeliveryReportItem,
    HumanAttentionItem,
    StandingAuthorization,
    WhatsAppStandingAuthorizationService,
    _fingerprint,
)


class PostgresStandingAuthorizationRepository:
    """Durable storage boundary backed by additive WhatsApp policy tables."""

    def save_authorization(self, authorization: StandingAuthorization) -> None:
        with session_scope() as session:
            session.execute(
                text(
                    """
                    INSERT INTO public.whatsapp_standing_authorizations (
                        authorization_id, owner_admin_id,
                        channel_identity_hash, valid_from, valid_until, status,
                        allowed_routine_actions, blocked_high_risk_actions,
                        created_at, updated_at, revoked_at,
                        renewal_metadata, audit_metadata
                    ) VALUES (
                        CAST(:authorization_id AS UUID), :owner_admin_id,
                        :channel_hash, :valid_from, :valid_until, :status,
                        CAST(:allowed AS JSONB), CAST(:blocked AS JSONB),
                        :created_at, :updated_at, :revoked_at,
                        CAST(:renewal AS JSONB), CAST(:audit AS JSONB)
                    )
                    ON CONFLICT (channel_identity_hash) DO UPDATE SET
                        authorization_id = EXCLUDED.authorization_id,
                        owner_admin_id = EXCLUDED.owner_admin_id,
                        valid_from = EXCLUDED.valid_from,
                        valid_until = EXCLUDED.valid_until,
                        status = EXCLUDED.status,
                        allowed_routine_actions = EXCLUDED.allowed_routine_actions,
                        blocked_high_risk_actions = EXCLUDED.blocked_high_risk_actions,
                        updated_at = EXCLUDED.updated_at,
                        revoked_at = EXCLUDED.revoked_at,
                        renewal_metadata = EXCLUDED.renewal_metadata,
                        audit_metadata = EXCLUDED.audit_metadata
                    """
                ),
                {
                    "authorization_id": authorization.authorization_id,
                    "owner_admin_id": _numeric_actor_id(
                        authorization.owner_admin_id
                    ),
                    "channel_hash": _fingerprint(authorization.channel_identity),
                    "valid_from": authorization.valid_from,
                    "valid_until": authorization.valid_until,
                    "status": authorization.status.value,
                    "allowed": json.dumps(
                        sorted(authorization.allowed_routine_actions)
                    ),
                    "blocked": json.dumps(
                        sorted(authorization.blocked_high_risk_actions)
                    ),
                    "created_at": authorization.created_at,
                    "updated_at": authorization.updated_at,
                    "revoked_at": authorization.revoked_at,
                    "renewal": json.dumps(authorization.renewal_metadata),
                    "audit": json.dumps(authorization.audit_metadata),
                },
            )

    def get_authorization(
        self, channel_identity: str
    ) -> StandingAuthorization | None:
        with session_scope() as session:
            row = (
                session.execute(
                    text(
                        """
                        SELECT authorization_id, owner_admin_id, valid_from,
                               valid_until, status, allowed_routine_actions,
                               blocked_high_risk_actions, created_at, updated_at,
                               revoked_at, renewal_metadata, audit_metadata
                        FROM public.whatsapp_standing_authorizations
                        WHERE channel_identity_hash = :channel_hash
                        LIMIT 1
                        """
                    ),
                    {"channel_hash": _fingerprint(channel_identity)},
                )
                .mappings()
                .first()
            )
        if not row:
            return None
        return StandingAuthorization(
            authorization_id=str(row["authorization_id"]),
            owner_admin_id=str(row["owner_admin_id"]),
            channel_identity=channel_identity,
            valid_from=row["valid_from"],
            valid_until=row["valid_until"],
            status=AuthorizationStatus(str(row["status"])),
            allowed_routine_actions=frozenset(
                _json_collection(row["allowed_routine_actions"])
            ),
            blocked_high_risk_actions=frozenset(
                _json_collection(row["blocked_high_risk_actions"])
            ),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            revoked_at=row["revoked_at"],
            renewal_metadata=_json_mapping(row["renewal_metadata"]),
            audit_metadata=_json_mapping(row["audit_metadata"]),
        )

    def save_client_state(self, state: ClientAutomationState) -> None:
        with session_scope() as session:
            session.execute(
                text(
                    """
                    INSERT INTO public.whatsapp_client_automation_states (
                        channel_identity_hash, client_identity_hash, paused,
                        reason, paused_at, resumed_at,
                        conversation_reference, updated_at
                    ) VALUES (
                        :channel_hash, :client_hash, :paused, :reason,
                        :paused_at, :resumed_at, :conversation_reference,
                        :updated_at
                    )
                    ON CONFLICT (
                        channel_identity_hash, client_identity_hash
                    ) DO UPDATE SET
                        paused = EXCLUDED.paused,
                        reason = EXCLUDED.reason,
                        paused_at = EXCLUDED.paused_at,
                        resumed_at = EXCLUDED.resumed_at,
                        conversation_reference = EXCLUDED.conversation_reference,
                        updated_at = EXCLUDED.updated_at
                    """
                ),
                {
                    "channel_hash": _fingerprint(state.channel_identity),
                    "client_hash": _fingerprint(state.client_identity),
                    "paused": state.paused,
                    "reason": state.reason[:80],
                    "paused_at": state.paused_at,
                    "resumed_at": state.resumed_at,
                    "conversation_reference": (
                        str(state.conversation_reference)[:120]
                        if state.conversation_reference
                        else None
                    ),
                    "updated_at": state.updated_at,
                },
            )

    def get_client_state(
        self, channel_identity: str, client_identity: str
    ) -> ClientAutomationState | None:
        with session_scope() as session:
            row = (
                session.execute(
                    text(
                        """
                        SELECT paused, reason, paused_at, resumed_at,
                               conversation_reference, updated_at
                        FROM public.whatsapp_client_automation_states
                        WHERE channel_identity_hash = :channel_hash
                          AND client_identity_hash = :client_hash
                        LIMIT 1
                        """
                    ),
                    {
                        "channel_hash": _fingerprint(channel_identity),
                        "client_hash": _fingerprint(client_identity),
                    },
                )
                .mappings()
                .first()
            )
        if not row:
            return None
        return ClientAutomationState(
            channel_identity=channel_identity,
            client_identity=client_identity,
            paused=bool(row["paused"]),
            reason=str(row["reason"]),
            paused_at=row["paused_at"],
            resumed_at=row["resumed_at"],
            conversation_reference=row["conversation_reference"],
            updated_at=row["updated_at"],
        )

    def claim_webhook(
        self, channel_identity: str, webhook_id: str, received_at: datetime
    ) -> bool:
        with session_scope() as session:
            claimed = session.execute(
                text(
                    """
                    INSERT INTO public.whatsapp_webhook_receipts (
                        channel_identity_hash, webhook_id_hash, received_at
                    ) VALUES (:channel_hash, :webhook_hash, :received_at)
                    ON CONFLICT (
                        channel_identity_hash, webhook_id_hash
                    ) DO NOTHING
                    RETURNING id
                    """
                ),
                {
                    "channel_hash": _fingerprint(channel_identity),
                    "webhook_hash": _fingerprint(webhook_id),
                    "received_at": received_at,
                },
            ).scalar_one_or_none()
        return claimed is not None

    def get_delivery_attempt(
        self, idempotency_key: str
    ) -> DeliveryAttemptState | None:
        with session_scope() as session:
            row = (
                session.execute(
                    text(
                        """
                        SELECT attempts, delivered, last_attempt_at,
                               channel_identity_hash, client_identity_hash,
                               last_error_category, in_flight
                        FROM public.whatsapp_delivery_attempts
                        WHERE idempotency_key_hash = :key_hash
                        LIMIT 1
                        """
                    ),
                    {"key_hash": _fingerprint(idempotency_key)},
                )
                .mappings()
                .first()
            )
        if not row:
            return None
        return DeliveryAttemptState(
            idempotency_key=idempotency_key,
            attempts=int(row["attempts"]),
            delivered=bool(row["delivered"]),
            last_attempt_at=row["last_attempt_at"],
            channel_fingerprint=str(row["channel_identity_hash"]),
            client_fingerprint=str(row["client_identity_hash"]),
            last_error_category=row["last_error_category"],
            in_flight=bool(row["in_flight"]),
        )

    def save_delivery_attempt(self, state: DeliveryAttemptState) -> None:
        with session_scope() as session:
            session.execute(
                text(
                    """
                    INSERT INTO public.whatsapp_delivery_attempts (
                        idempotency_key_hash, channel_identity_hash,
                        client_identity_hash, attempts, delivered,
                        last_attempt_at, last_error_category, in_flight
                    ) VALUES (
                        :key_hash, :channel_hash, :client_hash, :attempts,
                        :delivered, :last_attempt_at, :last_error_category
                        , :in_flight
                    )
                    ON CONFLICT (idempotency_key_hash) DO UPDATE SET
                        attempts = EXCLUDED.attempts,
                        delivered = EXCLUDED.delivered,
                        last_attempt_at = EXCLUDED.last_attempt_at,
                        last_error_category = EXCLUDED.last_error_category,
                        in_flight = EXCLUDED.in_flight
                    """
                ),
                {
                    "key_hash": _fingerprint(state.idempotency_key),
                    "channel_hash": state.channel_fingerprint,
                    "client_hash": state.client_fingerprint,
                    "attempts": state.attempts,
                    "delivered": state.delivered,
                    "last_attempt_at": state.last_attempt_at,
                    "last_error_category": state.last_error_category,
                    "in_flight": state.in_flight,
                },
            )

    def reserve_delivery_attempt(
        self,
        *,
        idempotency_key: str,
        channel_fingerprint: str,
        client_fingerprint: str,
        attempted_at: datetime,
        max_attempts: int,
    ) -> tuple[str, DeliveryAttemptState | None]:
        key_hash = _fingerprint(idempotency_key)
        with session_scope() as session:
            session.execute(
                text(
                    """
                    SELECT pg_advisory_xact_lock(
                        hashtextextended(:key_hash, 0)
                    )
                    """
                ),
                {"key_hash": key_hash},
            )
            row = (
                session.execute(
                    text(
                        """
                        SELECT attempts, delivered, in_flight,
                               last_attempt_at, last_error_category
                        FROM public.whatsapp_delivery_attempts
                        WHERE idempotency_key_hash = :key_hash
                        FOR UPDATE
                        """
                    ),
                    {"key_hash": key_hash},
                )
                .mappings()
                .first()
            )
            if row and (bool(row["delivered"]) or bool(row["in_flight"])):
                return "duplicate", None
            if row and int(row["attempts"]) >= max_attempts:
                return "exhausted", None
            attempts = int(row["attempts"]) + 1 if row else 1
            session.execute(
                text(
                    """
                    INSERT INTO public.whatsapp_delivery_attempts (
                        idempotency_key_hash, channel_identity_hash,
                        client_identity_hash, attempts, delivered,
                        last_attempt_at, last_error_category, in_flight
                    ) VALUES (
                        :key_hash, :channel_hash, :client_hash, :attempts,
                        FALSE, :attempted_at, NULL, TRUE
                    )
                    ON CONFLICT (idempotency_key_hash) DO UPDATE SET
                        attempts = EXCLUDED.attempts,
                        delivered = FALSE,
                        last_attempt_at = EXCLUDED.last_attempt_at,
                        last_error_category = NULL,
                        in_flight = TRUE
                    """
                ),
                {
                    "key_hash": key_hash,
                    "channel_hash": channel_fingerprint,
                    "client_hash": client_fingerprint,
                    "attempts": attempts,
                    "attempted_at": attempted_at,
                },
            )
        return (
            "reserved",
            DeliveryAttemptState(
                idempotency_key=idempotency_key,
                attempts=attempts,
                delivered=False,
                last_attempt_at=attempted_at,
                channel_fingerprint=channel_fingerprint,
                client_fingerprint=client_fingerprint,
                in_flight=True,
            ),
        )

    def register_client_delivery(
        self, channel_identity: str, client_identity: str, attempted_at: datetime
    ) -> int:
        with session_scope() as session:
            count = session.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM public.whatsapp_delivery_attempts
                    WHERE channel_identity_hash = :channel_hash
                      AND client_identity_hash = :client_hash
                      AND last_attempt_at > :attempted_at - INTERVAL '1 minute'
                    """
                ),
                {
                    "channel_hash": _fingerprint(channel_identity),
                    "client_hash": _fingerprint(client_identity),
                    "attempted_at": attempted_at,
                },
            ).scalar_one()
        # The just-reserved attempt is already visible in this count.
        return int(count or 0)

    def append_audit(self, event: AutomationAuditEvent) -> None:
        with session_scope() as session:
            session.execute(
                text(
                    """
                    INSERT INTO public.whatsapp_automation_audit_events (
                        event_type, actor_fingerprint, channel_fingerprint,
                        client_fingerprint, authorization_id, metadata,
                        created_at
                    ) VALUES (
                        :event_type, :actor_fingerprint, :channel_fingerprint,
                        :client_fingerprint, CAST(:authorization_id AS UUID),
                        CAST(:metadata AS JSONB), :created_at
                    )
                    """
                ),
                {
                    "event_type": event.event_type[:80],
                    "actor_fingerprint": event.actor_fingerprint,
                    "channel_fingerprint": event.channel_fingerprint,
                    "client_fingerprint": event.client_fingerprint,
                    "authorization_id": event.authorization_id,
                    "metadata": json.dumps(event.metadata),
                    "created_at": event.created_at,
                },
            )

    def list_audit(
        self, channel_identity: str, since: datetime
    ) -> list[AutomationAuditEvent]:
        with session_scope() as session:
            rows = (
                session.execute(
                    text(
                        """
                        SELECT event_type, actor_fingerprint,
                               channel_fingerprint, client_fingerprint,
                               authorization_id, metadata, created_at
                        FROM public.whatsapp_automation_audit_events
                        WHERE channel_fingerprint = :channel_hash
                          AND created_at >= :since
                        ORDER BY created_at
                        """
                    ),
                    {
                        "channel_hash": _fingerprint(channel_identity),
                        "since": since,
                    },
                )
                .mappings()
                .all()
            )
        return [
            AutomationAuditEvent(
                event_type=str(row["event_type"]),
                actor_fingerprint=str(row["actor_fingerprint"]),
                channel_fingerprint=str(row["channel_fingerprint"]),
                client_fingerprint=row["client_fingerprint"],
                authorization_id=(
                    str(row["authorization_id"])
                    if row["authorization_id"]
                    else None
                ),
                metadata=_json_mapping(row["metadata"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def list_failed_deliveries(
        self, channel_identity: str, since: datetime
    ) -> list[FailedDeliveryReportItem]:
        with session_scope() as session:
            rows = (
                session.execute(
                    text(
                        """
                        SELECT idempotency_key_hash, client_identity_hash,
                               attempts, last_attempt_at, last_error_category
                        FROM public.whatsapp_delivery_attempts
                        WHERE channel_identity_hash = :channel_hash
                          AND delivered = FALSE
                          AND last_attempt_at >= :since
                        ORDER BY last_attempt_at DESC
                        """
                    ),
                    {
                        "channel_hash": _fingerprint(channel_identity),
                        "since": since,
                    },
                )
                .mappings()
                .all()
            )
        return [
            FailedDeliveryReportItem(
                idempotency_fingerprint=str(row["idempotency_key_hash"]),
                client_fingerprint=str(row["client_identity_hash"]),
                attempts=int(row["attempts"]),
                last_attempt_at=row["last_attempt_at"],
                error_category=str(
                    row["last_error_category"] or "delivery_incomplete"
                ),
            )
            for row in rows
        ]

    def list_clients_needing_attention(
        self, channel_identity: str
    ) -> list[HumanAttentionItem]:
        with session_scope() as session:
            rows = (
                session.execute(
                    text(
                        """
                        SELECT client_identity_hash, reason, updated_at
                        FROM public.whatsapp_client_automation_states
                        WHERE channel_identity_hash = :channel_hash
                          AND paused = TRUE
                        ORDER BY updated_at DESC
                        """
                    ),
                    {"channel_hash": _fingerprint(channel_identity)},
                )
                .mappings()
                .all()
            )
        return [
            HumanAttentionItem(
                client_fingerprint=str(row["client_identity_hash"]),
                reason=str(row["reason"]),
                updated_at=row["updated_at"],
            )
            for row in rows
        ]


def build_postgres_standing_authorization_service(
) -> WhatsAppStandingAuthorizationService:
    """Build the runtime service without reading or exposing secret values."""
    return WhatsAppStandingAuthorizationService(
        PostgresStandingAuthorizationRepository(),
        owner_authorizer=_is_verified_admin,
        max_delivery_attempts=3,
    )


def _is_verified_admin(actor_id: str) -> bool:
    try:
        numeric_id = _numeric_actor_id(actor_id)
    except ValueError:
        return False
    with session_scope() as session:
        eligible = session.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM public.users
                    WHERE id = :actor_id
                      AND UPPER(COALESCE(role, '')) = 'ADMIN'
                      AND email_verified = TRUE
                      AND UPPER(COALESCE(approval_status, '')) = 'APPROVED'
                )
                """
            ),
            {"actor_id": numeric_id},
        ).scalar_one()
    return bool(eligible)


def _numeric_actor_id(actor_id: str) -> int:
    normalized = str(actor_id or "").strip()
    if not normalized.isdigit():
        raise ValueError("Verified numeric administrator identity required.")
    return int(normalized)


def _json_collection(value: Any) -> list[str]:
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _json_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        value = json.loads(value)
    return dict(value) if isinstance(value, dict) else {}
