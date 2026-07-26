"""Deterministic standing authorization for routine WhatsApp automation.

This module is intentionally independent from webhook handling and delivery.
It makes authorization decisions only; it never sends a WhatsApp message.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from enum import Enum
import hashlib
import re
from threading import RLock
from typing import Any, Callable, Protocol
from uuid import uuid4


AUTHORIZATION_DAYS = 360
EXPIRY_WARNING_DAYS = 30


class AuthorizationStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    REVOKED = "revoked"
    EXPIRED = "expired"


class AutomationDecisionStatus(str, Enum):
    ALLOWED = "ALLOWED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    BLOCKED = "BLOCKED"
    PAUSED = "PAUSED"
    DUPLICATE_IGNORED = "DUPLICATE_IGNORED"
    RATE_LIMITED = "RATE_LIMITED"
    RETRY_EXHAUSTED = "RETRY_EXHAUSTED"


ROUTINE_ACTIONS = frozenset(
    {
        "greeting",
        "faq_reply",
        "approved_service_information",
        "lead_qualification",
        "collect_client_details",
        "appointment_enquiry",
        "approved_reminder",
        "routine_follow_up",
        "conversation_summary",
        "safe_handoff_notice",
    }
)

HIGH_RISK_ACTIONS = frozenset(
    {
        "payment_commitment",
        "refund_commitment",
        "unusual_discount",
        "legal_guarantee",
        "medical_guarantee",
        "financial_guarantee",
        "bulk_campaign",
        "sensitive_data_disclosure",
        "destructive_action",
        "production_deployment",
        "production_configuration",
        "database_migration",
        "secrets_change",
        "environment_change",
        "client_data_deletion",
        "unsupported_promise",
    }
)


class WhatsAppAuthorizationError(PermissionError):
    """Raised when a non-owner requests an authorization state change."""


@dataclass(frozen=True)
class StandingAuthorization:
    authorization_id: str
    owner_admin_id: str
    channel_identity: str
    valid_from: datetime
    valid_until: datetime
    status: AuthorizationStatus
    allowed_routine_actions: frozenset[str]
    blocked_high_risk_actions: frozenset[str]
    created_at: datetime
    updated_at: datetime
    revoked_at: datetime | None = None
    renewal_metadata: dict[str, Any] = field(default_factory=dict)
    audit_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ClientAutomationState:
    channel_identity: str
    client_identity: str
    paused: bool
    reason: str
    paused_at: datetime | None
    resumed_at: datetime | None
    conversation_reference: str | None
    updated_at: datetime


@dataclass(frozen=True)
class AutomationDecision:
    status: AutomationDecisionStatus
    action: str
    reason: str
    authorization_id: str | None = None
    repeated_approval_required: bool = False

    @property
    def allowed(self) -> bool:
        return self.status == AutomationDecisionStatus.ALLOWED


@dataclass(frozen=True)
class AutomationAuditEvent:
    event_type: str
    actor_fingerprint: str
    channel_fingerprint: str
    client_fingerprint: str | None
    authorization_id: str | None
    metadata: dict[str, Any]
    created_at: datetime


@dataclass(frozen=True)
class DeliveryAttemptState:
    idempotency_key: str
    attempts: int
    delivered: bool
    last_attempt_at: datetime
    channel_fingerprint: str = ""
    client_fingerprint: str = ""
    last_error_category: str | None = None
    in_flight: bool = False


@dataclass(frozen=True)
class DailyOwnerReport:
    channel_fingerprint: str
    report_date: str
    authorization_status: str
    valid_until: datetime | None
    expiry_warning: bool
    routine_allowed: int
    approval_required: int
    paused_or_blocked: int
    duplicate_webhooks: int
    rate_limited: int


@dataclass(frozen=True)
class FailedDeliveryReportItem:
    idempotency_fingerprint: str
    client_fingerprint: str
    attempts: int
    last_attempt_at: datetime
    error_category: str


@dataclass(frozen=True)
class HumanAttentionItem:
    client_fingerprint: str
    reason: str
    updated_at: datetime


class StandingAuthorizationRepository(Protocol):
    def save_authorization(self, authorization: StandingAuthorization) -> None: ...

    def get_authorization(
        self, channel_identity: str
    ) -> StandingAuthorization | None: ...

    def save_client_state(self, state: ClientAutomationState) -> None: ...

    def get_client_state(
        self, channel_identity: str, client_identity: str
    ) -> ClientAutomationState | None: ...

    def claim_webhook(
        self, channel_identity: str, webhook_id: str, received_at: datetime
    ) -> bool: ...

    def get_delivery_attempt(
        self, idempotency_key: str
    ) -> DeliveryAttemptState | None: ...

    def save_delivery_attempt(self, state: DeliveryAttemptState) -> None: ...

    def reserve_delivery_attempt(
        self,
        *,
        idempotency_key: str,
        channel_fingerprint: str,
        client_fingerprint: str,
        attempted_at: datetime,
        max_attempts: int,
    ) -> tuple[str, DeliveryAttemptState | None]: ...

    def register_client_delivery(
        self, channel_identity: str, client_identity: str, attempted_at: datetime
    ) -> int: ...

    def append_audit(self, event: AutomationAuditEvent) -> None: ...

    def list_audit(
        self, channel_identity: str, since: datetime
    ) -> list[AutomationAuditEvent]: ...

    def list_failed_deliveries(
        self, channel_identity: str, since: datetime
    ) -> list[FailedDeliveryReportItem]: ...

    def list_clients_needing_attention(
        self, channel_identity: str
    ) -> list[HumanAttentionItem]: ...


class InMemoryStandingAuthorizationRepository:
    """Isolated test repository; not intended for production durability."""

    def __init__(self) -> None:
        self.authorizations: dict[str, StandingAuthorization] = {}
        self.client_states: dict[tuple[str, str], ClientAutomationState] = {}
        self.webhooks: set[tuple[str, str]] = set()
        self.delivery_attempts: dict[str, DeliveryAttemptState] = {}
        self.client_deliveries: dict[tuple[str, str], deque[datetime]] = defaultdict(deque)
        self.audit_events: list[tuple[str, AutomationAuditEvent]] = []
        self._lock = RLock()

    def save_authorization(self, authorization: StandingAuthorization) -> None:
        self.authorizations[authorization.channel_identity] = authorization

    def get_authorization(
        self, channel_identity: str
    ) -> StandingAuthorization | None:
        return self.authorizations.get(channel_identity)

    def save_client_state(self, state: ClientAutomationState) -> None:
        self.client_states[(state.channel_identity, state.client_identity)] = state

    def get_client_state(
        self, channel_identity: str, client_identity: str
    ) -> ClientAutomationState | None:
        return self.client_states.get((channel_identity, client_identity))

    def claim_webhook(
        self, channel_identity: str, webhook_id: str, received_at: datetime
    ) -> bool:
        del received_at
        key = (channel_identity, webhook_id)
        with self._lock:
            if key in self.webhooks:
                return False
            self.webhooks.add(key)
            return True

    def get_delivery_attempt(
        self, idempotency_key: str
    ) -> DeliveryAttemptState | None:
        return self.delivery_attempts.get(idempotency_key)

    def save_delivery_attempt(self, state: DeliveryAttemptState) -> None:
        with self._lock:
            self.delivery_attempts[state.idempotency_key] = state

    def reserve_delivery_attempt(
        self,
        *,
        idempotency_key: str,
        channel_fingerprint: str,
        client_fingerprint: str,
        attempted_at: datetime,
        max_attempts: int,
    ) -> tuple[str, DeliveryAttemptState | None]:
        with self._lock:
            prior = self.delivery_attempts.get(idempotency_key)
            if prior and (prior.delivered or prior.in_flight):
                return "duplicate", prior
            if prior and prior.attempts >= max_attempts:
                return "exhausted", prior
            state = DeliveryAttemptState(
                idempotency_key=idempotency_key,
                attempts=(prior.attempts if prior else 0) + 1,
                delivered=False,
                last_attempt_at=attempted_at,
                channel_fingerprint=channel_fingerprint,
                client_fingerprint=client_fingerprint,
                last_error_category=None,
                in_flight=True,
            )
            self.delivery_attempts[idempotency_key] = state
            return "reserved", state

    def register_client_delivery(
        self, channel_identity: str, client_identity: str, attempted_at: datetime
    ) -> int:
        key = (channel_identity, client_identity)
        window = self.client_deliveries[key]
        cutoff = attempted_at - timedelta(minutes=1)
        while window and window[0] <= cutoff:
            window.popleft()
        window.append(attempted_at)
        return len(window)

    def append_audit(self, event: AutomationAuditEvent) -> None:
        self.audit_events.append((event.channel_fingerprint, event))

    def list_audit(
        self, channel_identity: str, since: datetime
    ) -> list[AutomationAuditEvent]:
        channel_fingerprint = _fingerprint(channel_identity)
        return [
            event
            for fingerprint, event in self.audit_events
            if fingerprint == channel_fingerprint and event.created_at >= since
        ]

    def list_failed_deliveries(
        self, channel_identity: str, since: datetime
    ) -> list[FailedDeliveryReportItem]:
        channel_fingerprint = _fingerprint(channel_identity)
        return [
            FailedDeliveryReportItem(
                idempotency_fingerprint=_fingerprint(state.idempotency_key),
                client_fingerprint=state.client_fingerprint,
                attempts=state.attempts,
                last_attempt_at=state.last_attempt_at,
                error_category=state.last_error_category or "delivery_incomplete",
            )
            for state in self.delivery_attempts.values()
            if state.channel_fingerprint == channel_fingerprint
            and not state.delivered
            and state.last_attempt_at >= since
        ]

    def list_clients_needing_attention(
        self, channel_identity: str
    ) -> list[HumanAttentionItem]:
        return [
            HumanAttentionItem(
                client_fingerprint=_fingerprint(state.client_identity),
                reason=state.reason,
                updated_at=state.updated_at,
            )
            for state in self.client_states.values()
            if state.channel_identity == channel_identity and state.paused
        ]


class WhatsAppStandingAuthorizationService:
    """Evaluate standing authorization without using an LLM."""

    def __init__(
        self,
        repository: StandingAuthorizationRepository,
        *,
        owner_authorizer: Callable[[str], bool],
        max_delivery_attempts: int = 3,
        per_client_per_minute_limit: int = 10,
    ) -> None:
        self.repository = repository
        self.owner_authorizer = owner_authorizer
        self.max_delivery_attempts = max(1, max_delivery_attempts)
        self.per_client_per_minute_limit = max(1, per_client_per_minute_limit)

    def activate(
        self,
        *,
        actor_id: str,
        channel_identity: str,
        now: datetime | None = None,
        renewal_metadata: dict[str, Any] | None = None,
        audit_metadata: dict[str, Any] | None = None,
    ) -> StandingAuthorization:
        self._require_owner(actor_id)
        current = _aware(now)
        authorization = StandingAuthorization(
            authorization_id=str(uuid4()),
            owner_admin_id=actor_id,
            channel_identity=channel_identity,
            valid_from=current,
            valid_until=current + timedelta(days=AUTHORIZATION_DAYS),
            status=AuthorizationStatus.ACTIVE,
            allowed_routine_actions=ROUTINE_ACTIONS,
            blocked_high_risk_actions=HIGH_RISK_ACTIONS,
            created_at=current,
            updated_at=current,
            renewal_metadata=_sanitize_metadata(renewal_metadata or {}),
            audit_metadata=_sanitize_metadata(audit_metadata or {}),
        )
        self.repository.save_authorization(authorization)
        self._audit(
            "AUTHORIZATION_ACTIVATED",
            actor_id,
            channel_identity,
            authorization.authorization_id,
            now=current,
        )
        return authorization

    def renew(
        self,
        *,
        actor_id: str,
        channel_identity: str,
        now: datetime | None = None,
        renewal_metadata: dict[str, Any] | None = None,
    ) -> StandingAuthorization:
        authorization = self._owner_authorization(actor_id, channel_identity)
        current = _aware(now)
        renewed = replace(
            authorization,
            valid_from=current,
            valid_until=current + timedelta(days=AUTHORIZATION_DAYS),
            status=AuthorizationStatus.ACTIVE,
            updated_at=current,
            revoked_at=None,
            renewal_metadata=_sanitize_metadata(renewal_metadata or {}),
        )
        self.repository.save_authorization(renewed)
        self._audit(
            "AUTHORIZATION_RENEWED",
            actor_id,
            channel_identity,
            renewed.authorization_id,
            now=current,
        )
        return renewed

    def pause_global(
        self, *, actor_id: str, channel_identity: str, now: datetime | None = None
    ) -> StandingAuthorization:
        return self._set_global_status(
            actor_id, channel_identity, AuthorizationStatus.PAUSED, now
        )

    def resume_global(
        self, *, actor_id: str, channel_identity: str, now: datetime | None = None
    ) -> StandingAuthorization:
        authorization = self._owner_authorization(actor_id, channel_identity)
        current = _aware(now)
        if authorization.status == AuthorizationStatus.REVOKED:
            raise WhatsAppAuthorizationError("Revoked authorization cannot be resumed.")
        if current >= authorization.valid_until:
            expired = replace(
                authorization,
                status=AuthorizationStatus.EXPIRED,
                updated_at=current,
            )
            self.repository.save_authorization(expired)
            raise WhatsAppAuthorizationError("Expired authorization must be renewed.")
        return self._set_global_status(
            actor_id, channel_identity, AuthorizationStatus.ACTIVE, current
        )

    def revoke(
        self, *, actor_id: str, channel_identity: str, now: datetime | None = None
    ) -> StandingAuthorization:
        authorization = self._owner_authorization(actor_id, channel_identity)
        current = _aware(now)
        revoked = replace(
            authorization,
            status=AuthorizationStatus.REVOKED,
            revoked_at=current,
            updated_at=current,
        )
        self.repository.save_authorization(revoked)
        self._audit(
            "AUTHORIZATION_REVOKED",
            actor_id,
            channel_identity,
            revoked.authorization_id,
            now=current,
        )
        return revoked

    def record_owner_manual_reply(
        self,
        *,
        actor_id: str,
        channel_identity: str,
        client_identity: str,
        conversation_reference: str | None = None,
        now: datetime | None = None,
    ) -> ClientAutomationState:
        authorization = self._owner_authorization(actor_id, channel_identity)
        current = _aware(now)
        state = ClientAutomationState(
            channel_identity=channel_identity,
            client_identity=client_identity,
            paused=True,
            reason="OWNER_MANUAL_TAKEOVER",
            paused_at=current,
            resumed_at=None,
            conversation_reference=conversation_reference,
            updated_at=current,
        )
        self.repository.save_client_state(state)
        self._audit(
            "CLIENT_AUTOMATION_PAUSED",
            actor_id,
            channel_identity,
            authorization.authorization_id,
            client_identity=client_identity,
            metadata={"reason": state.reason},
            now=current,
        )
        return state

    def resume_client(
        self,
        *,
        actor_id: str,
        channel_identity: str,
        client_identity: str,
        now: datetime | None = None,
    ) -> ClientAutomationState:
        authorization = self._owner_authorization(actor_id, channel_identity)
        current = _aware(now)
        previous = self.repository.get_client_state(
            channel_identity, client_identity
        )
        state = ClientAutomationState(
            channel_identity=channel_identity,
            client_identity=client_identity,
            paused=False,
            reason="OWNER_RESUMED",
            paused_at=previous.paused_at if previous else None,
            resumed_at=current,
            conversation_reference=(
                previous.conversation_reference if previous else None
            ),
            updated_at=current,
        )
        self.repository.save_client_state(state)
        self._audit(
            "CLIENT_AUTOMATION_RESUMED",
            actor_id,
            channel_identity,
            authorization.authorization_id,
            client_identity=client_identity,
            now=current,
        )
        return state

    def evaluate(
        self,
        *,
        channel_identity: str,
        client_identity: str,
        action: str,
        now: datetime | None = None,
    ) -> AutomationDecision:
        current = _aware(now)
        clean_action = str(action or "").strip().lower()
        authorization = self.repository.get_authorization(channel_identity)
        if authorization is None:
            return self._decision(
                AutomationDecisionStatus.BLOCKED,
                action=clean_action,
                reason="Standing authorization is missing.",
                channel_identity=channel_identity,
                client_identity=client_identity,
                authorization_id=None,
                now=current,
            )
        if current >= authorization.valid_until:
            if authorization.status != AuthorizationStatus.EXPIRED:
                authorization = replace(
                    authorization,
                    status=AuthorizationStatus.EXPIRED,
                    updated_at=current,
                )
                self.repository.save_authorization(authorization)
                self._audit(
                    "AUTHORIZATION_EXPIRED",
                    authorization.owner_admin_id,
                    channel_identity,
                    authorization.authorization_id,
                    now=current,
                )
            return self._decision(
                AutomationDecisionStatus.BLOCKED,
                action=clean_action,
                reason="Standing authorization expired; outbound automation stopped.",
                channel_identity=channel_identity,
                client_identity=client_identity,
                authorization_id=authorization.authorization_id,
                now=current,
            )
        if authorization.status == AuthorizationStatus.REVOKED:
            return self._decision(
                AutomationDecisionStatus.BLOCKED,
                action=clean_action,
                reason="Standing authorization was revoked.",
                channel_identity=channel_identity,
                client_identity=client_identity,
                authorization_id=authorization.authorization_id,
                now=current,
            )
        if authorization.status == AuthorizationStatus.PAUSED:
            return self._decision(
                AutomationDecisionStatus.PAUSED,
                action=clean_action,
                reason="Global emergency pause is active.",
                channel_identity=channel_identity,
                client_identity=client_identity,
                authorization_id=authorization.authorization_id,
                now=current,
            )
        client_state = self.repository.get_client_state(
            channel_identity, client_identity
        )
        if client_state and client_state.paused:
            return self._decision(
                AutomationDecisionStatus.PAUSED,
                action=clean_action,
                reason="Owner manual takeover is active for this client.",
                channel_identity=channel_identity,
                client_identity=client_identity,
                authorization_id=authorization.authorization_id,
                now=current,
            )
        if clean_action in authorization.blocked_high_risk_actions:
            return self._decision(
                AutomationDecisionStatus.APPROVAL_REQUIRED,
                action=clean_action,
                reason="High-risk action requires explicit owner approval.",
                channel_identity=channel_identity,
                client_identity=client_identity,
                authorization_id=authorization.authorization_id,
                repeated_approval_required=True,
                now=current,
            )
        if clean_action in authorization.allowed_routine_actions:
            return self._decision(
                AutomationDecisionStatus.ALLOWED,
                action=clean_action,
                reason="Routine action covered by active standing authorization.",
                channel_identity=channel_identity,
                client_identity=client_identity,
                authorization_id=authorization.authorization_id,
                repeated_approval_required=False,
                now=current,
            )
        return self._decision(
            AutomationDecisionStatus.APPROVAL_REQUIRED,
            action=clean_action,
            reason="Unknown or unsupported action requires owner review.",
            channel_identity=channel_identity,
            client_identity=client_identity,
            authorization_id=authorization.authorization_id,
            repeated_approval_required=True,
            now=current,
        )

    def claim_webhook(
        self,
        *,
        channel_identity: str,
        webhook_id: str,
        now: datetime | None = None,
    ) -> AutomationDecision:
        current = _aware(now)
        claimed = self.repository.claim_webhook(
            channel_identity, webhook_id, current
        )
        if claimed:
            return AutomationDecision(
                AutomationDecisionStatus.ALLOWED,
                "process_inbound_webhook",
                "Webhook claimed exactly once.",
            )
        self._audit(
            "DUPLICATE_WEBHOOK_IGNORED",
            "system",
            channel_identity,
            None,
            now=current,
        )
        return AutomationDecision(
            AutomationDecisionStatus.DUPLICATE_IGNORED,
            "process_inbound_webhook",
            "Duplicate webhook ignored.",
        )

    def begin_delivery_attempt(
        self,
        *,
        channel_identity: str,
        client_identity: str,
        action: str,
        idempotency_key: str,
        now: datetime | None = None,
    ) -> AutomationDecision:
        current = _aware(now)
        authorization_decision = self.evaluate(
            channel_identity=channel_identity,
            client_identity=client_identity,
            action=action,
            now=current,
        )
        if not authorization_decision.allowed:
            return authorization_decision
        reservation, _ = self.repository.reserve_delivery_attempt(
            idempotency_key=idempotency_key,
            channel_fingerprint=_fingerprint(channel_identity),
            client_fingerprint=_fingerprint(client_identity),
            attempted_at=current,
            max_attempts=self.max_delivery_attempts,
        )
        if reservation == "duplicate":
            return AutomationDecision(
                AutomationDecisionStatus.DUPLICATE_IGNORED,
                "outbound_delivery",
                "Delivery is already reserved or completed.",
            )
        if reservation == "exhausted":
            return AutomationDecision(
                AutomationDecisionStatus.RETRY_EXHAUSTED,
                "outbound_delivery",
                "Safe delivery retry limit reached.",
            )
        rate_count = self.repository.register_client_delivery(
            channel_identity, client_identity, current
        )
        if rate_count > self.per_client_per_minute_limit:
            self.mark_delivery_failed(
                idempotency_key=idempotency_key,
                error_category="rate_limited",
                now=current,
            )
            self._audit(
                "DELIVERY_RATE_LIMITED",
                "system",
                channel_identity,
                None,
                client_identity=client_identity,
                now=current,
            )
            return AutomationDecision(
                AutomationDecisionStatus.RATE_LIMITED,
                "outbound_delivery",
                "Per-client delivery rate limit reached.",
            )
        return AutomationDecision(
            AutomationDecisionStatus.ALLOWED,
            "outbound_delivery",
            "Delivery attempt reserved.",
        )

    def mark_delivery_complete(
        self, *, idempotency_key: str, now: datetime | None = None
    ) -> None:
        current = _aware(now)
        prior = self.repository.get_delivery_attempt(idempotency_key)
        if prior is None:
            raise ValueError("Delivery attempt was not reserved.")
        self.repository.save_delivery_attempt(
            replace(
                prior,
                delivered=True,
                last_attempt_at=current,
                last_error_category=None,
                in_flight=False,
            )
        )

    def mark_delivery_failed(
        self,
        *,
        idempotency_key: str,
        error_category: str,
        now: datetime | None = None,
    ) -> None:
        current = _aware(now)
        prior = self.repository.get_delivery_attempt(idempotency_key)
        if prior is None:
            raise ValueError("Delivery attempt was not reserved.")
        self.repository.save_delivery_attempt(
            replace(
                prior,
                delivered=False,
                last_attempt_at=current,
                last_error_category=_safe_error_category(error_category),
                in_flight=False,
            )
        )

    def build_daily_owner_report(
        self,
        *,
        channel_identity: str,
        now: datetime | None = None,
    ) -> DailyOwnerReport:
        current = _aware(now)
        authorization = self.repository.get_authorization(channel_identity)
        events = self.repository.list_audit(
            channel_identity, current - timedelta(days=1)
        )
        counts = defaultdict(int)
        for event in events:
            counts[event.event_type] += 1
        return DailyOwnerReport(
            channel_fingerprint=_fingerprint(channel_identity),
            report_date=current.date().isoformat(),
            authorization_status=(
                authorization.status.value if authorization else "missing"
            ),
            valid_until=authorization.valid_until if authorization else None,
            expiry_warning=(
                bool(authorization)
                and authorization.valid_until - current
                <= timedelta(days=EXPIRY_WARNING_DAYS)
            ),
            routine_allowed=counts["ROUTINE_ACTION_ALLOWED"],
            approval_required=counts["APPROVAL_REQUIRED"],
            paused_or_blocked=(
                counts["CLIENT_AUTOMATION_PAUSED"]
                + counts["AUTHORIZATION_EXPIRED"]
                + counts["AUTHORIZATION_REVOKED"]
            ),
            duplicate_webhooks=counts["DUPLICATE_WEBHOOK_IGNORED"],
            rate_limited=counts["DELIVERY_RATE_LIMITED"],
        )

    def list_failed_deliveries(
        self,
        *,
        channel_identity: str,
        now: datetime | None = None,
    ) -> list[FailedDeliveryReportItem]:
        current = _aware(now)
        return self.repository.list_failed_deliveries(
            channel_identity, current - timedelta(days=1)
        )

    def list_clients_needing_human_attention(
        self, *, channel_identity: str
    ) -> list[HumanAttentionItem]:
        return self.repository.list_clients_needing_attention(channel_identity)

    def _set_global_status(
        self,
        actor_id: str,
        channel_identity: str,
        status: AuthorizationStatus,
        now: datetime | None,
    ) -> StandingAuthorization:
        authorization = self._owner_authorization(actor_id, channel_identity)
        current = _aware(now)
        updated = replace(
            authorization,
            status=status,
            updated_at=current,
        )
        self.repository.save_authorization(updated)
        self._audit(
            f"AUTHORIZATION_{status.value.upper()}",
            actor_id,
            channel_identity,
            updated.authorization_id,
            now=current,
        )
        return updated

    def _decision(
        self,
        status: AutomationDecisionStatus,
        *,
        action: str,
        reason: str,
        channel_identity: str,
        client_identity: str,
        authorization_id: str | None,
        repeated_approval_required: bool = False,
        now: datetime | None = None,
    ) -> AutomationDecision:
        event_type = {
            AutomationDecisionStatus.ALLOWED: "ROUTINE_ACTION_ALLOWED",
            AutomationDecisionStatus.APPROVAL_REQUIRED: "APPROVAL_REQUIRED",
            AutomationDecisionStatus.PAUSED: "AUTOMATION_PAUSED",
            AutomationDecisionStatus.BLOCKED: "AUTOMATION_BLOCKED",
        }.get(status, "AUTOMATION_DECISION")
        self._audit(
            event_type,
            "system",
            channel_identity,
            authorization_id,
            client_identity=client_identity,
            metadata={"action": action, "status": status.value},
            now=now,
        )
        return AutomationDecision(
            status=status,
            action=action,
            reason=reason,
            authorization_id=authorization_id,
            repeated_approval_required=repeated_approval_required,
        )

    def _owner_authorization(
        self, actor_id: str, channel_identity: str
    ) -> StandingAuthorization:
        self._require_owner(actor_id)
        authorization = self.repository.get_authorization(channel_identity)
        if authorization is None:
            raise WhatsAppAuthorizationError("Standing authorization not found.")
        if authorization.owner_admin_id != actor_id:
            raise WhatsAppAuthorizationError("Owner identity does not match.")
        return authorization

    def _require_owner(self, actor_id: str) -> None:
        if not self.owner_authorizer(str(actor_id or "")):
            raise WhatsAppAuthorizationError("Owner authorization required.")

    def _audit(
        self,
        event_type: str,
        actor_id: str,
        channel_identity: str,
        authorization_id: str | None,
        *,
        client_identity: str | None = None,
        metadata: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> None:
        self.repository.append_audit(
            AutomationAuditEvent(
                event_type=event_type,
                actor_fingerprint=_fingerprint(actor_id),
                channel_fingerprint=_fingerprint(channel_identity),
                client_fingerprint=(
                    _fingerprint(client_identity) if client_identity else None
                ),
                authorization_id=authorization_id,
                metadata=_sanitize_metadata(metadata or {}),
                created_at=_aware(now),
            )
        )


def _sanitize_metadata(value: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    sensitive_markers = {
        "access_token", "authorization", "body", "credential", "email",
        "message", "password", "phone", "secret", "token", "traceback",
    }
    for raw_key, raw_value in value.items():
        key = str(raw_key)[:80]
        lowered = key.lower()
        if any(marker in lowered for marker in sensitive_markers):
            safe[key] = "[REDACTED]"
        elif isinstance(raw_value, bool | int | float) or raw_value is None:
            safe[key] = raw_value
        else:
            text_value = str(raw_value)
            if any(marker in text_value.lower() for marker in sensitive_markers):
                safe[key] = "[REDACTED]"
            else:
                safe[key] = text_value[:200]
    return safe


def _fingerprint(value: str | None) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:16]


def _aware(value: datetime | None) -> datetime:
    result = value or datetime.now(timezone.utc)
    if result.tzinfo is None:
        raise ValueError("Timezone-aware datetime required.")
    return result.astimezone(timezone.utc)


def classify_inbound_action(message: str) -> str:
    """Classify inbound text deterministically; unknown text fails closed."""
    normalized = re.sub(r"\s+", " ", str(message or "").strip().lower())
    if not normalized:
        return "unknown"
    high_risk_patterns = (
        (r"\b(refund|money back|paise wapas)\b", "refund_commitment"),
        (r"\b(payment|pay now|invoice|charge)\b", "payment_commitment"),
        (r"\b(discount|offer price|special price)\b", "unusual_discount"),
        (r"\b(guarantee|guaranteed|sure profit|fixed return)\b", "financial_guarantee"),
        (r"\b(legal advice|lawsuit|court)\b", "legal_guarantee"),
        (r"\b(medical advice|diagnosis|medicine)\b", "medical_guarantee"),
        (r"\b(delete my data|erase my data)\b", "client_data_deletion"),
        (r"\b(password|access token|secret key|otp)\b", "sensitive_data_disclosure"),
    )
    for pattern, action in high_risk_patterns:
        if re.search(pattern, normalized):
            return action
    routine_patterns = (
        (r"^(hi|hello|hey|namaste|good (morning|afternoon|evening))\b", "greeting"),
        (r"\b(appointment|meeting|call back|callback|book a call)\b", "appointment_enquiry"),
        (r"\b(remind|reminder)\b", "approved_reminder"),
        (r"\b(follow up|follow-up|status update)\b", "routine_follow_up"),
        (r"\b(my name|my email|my number|contact details)\b", "collect_client_details"),
        (r"\b(interested|service chahiye|want service|pricing information)\b", "lead_qualification"),
        (r"\b(service|services|how does|what is|help|faq|information|details)\b", "faq_reply"),
    )
    for pattern, action in routine_patterns:
        if re.search(pattern, normalized):
            return action
    return "unknown"


def _safe_error_category(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9_-]+", "_", str(value or "").lower()).strip("_")
    return normalized[:80] or "delivery_failed"
