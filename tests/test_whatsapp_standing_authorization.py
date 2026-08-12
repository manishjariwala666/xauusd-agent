from __future__ import annotations

from datetime import datetime, timedelta, timezone
import inspect

import pytest

from services import whatsapp_standing_authorization as authorization_module
from services.whatsapp_standing_authorization import (
    AUTHORIZATION_DAYS,
    AuthorizationStatus,
    AutomationDecisionStatus,
    InMemoryStandingAuthorizationRepository,
    WhatsAppAuthorizationError,
    WhatsAppStandingAuthorizationService,
)


NOW = datetime(2026, 7, 26, 12, 0, tzinfo=timezone.utc)
OWNER = "owner-admin"
CHANNEL = "whatsapp-business-account"
CLIENT_A = "client-a"
CLIENT_B = "client-b"


def service(
    *,
    repository: InMemoryStandingAuthorizationRepository | None = None,
    delivery_limit: int = 10,
) -> tuple[
    WhatsAppStandingAuthorizationService,
    InMemoryStandingAuthorizationRepository,
]:
    repo = repository or InMemoryStandingAuthorizationRepository()
    return (
        WhatsAppStandingAuthorizationService(
            repo,
            owner_authorizer=lambda actor_id: actor_id == OWNER,
            per_client_per_minute_limit=delivery_limit,
        ),
        repo,
    )


def active_service() -> tuple[
    WhatsAppStandingAuthorizationService,
    InMemoryStandingAuthorizationRepository,
]:
    standing, repo = service()
    standing.activate(actor_id=OWNER, channel_identity=CHANNEL, now=NOW)
    return standing, repo


def test_explicit_authorization_creates_exact_360_day_validity() -> None:
    standing, _ = service()

    authorization = standing.activate(
        actor_id=OWNER,
        channel_identity=CHANNEL,
        now=NOW,
    )

    assert authorization.status == AuthorizationStatus.ACTIVE
    assert authorization.valid_until == NOW + timedelta(days=AUTHORIZATION_DAYS)
    assert authorization.valid_until - authorization.valid_from == timedelta(
        days=360
    )


def test_routine_reply_is_allowed_during_active_period() -> None:
    standing, _ = active_service()

    decision = standing.evaluate(
        channel_identity=CHANNEL,
        client_identity=CLIENT_A,
        action="faq_reply",
        now=NOW + timedelta(days=1),
    )

    assert decision.allowed is True
    assert decision.status == AutomationDecisionStatus.ALLOWED


def test_routine_reply_does_not_request_repeated_approval() -> None:
    standing, _ = active_service()

    first = standing.evaluate(
        channel_identity=CHANNEL,
        client_identity=CLIENT_A,
        action="greeting",
        now=NOW,
    )
    second = standing.evaluate(
        channel_identity=CHANNEL,
        client_identity=CLIENT_A,
        action="routine_follow_up",
        now=NOW + timedelta(minutes=5),
    )

    assert first.allowed and second.allowed
    assert first.repeated_approval_required is False
    assert second.repeated_approval_required is False


def test_high_risk_request_requires_approval() -> None:
    standing, _ = active_service()

    decision = standing.evaluate(
        channel_identity=CHANNEL,
        client_identity=CLIENT_A,
        action="payment_commitment",
        now=NOW,
    )

    assert decision.status == AutomationDecisionStatus.APPROVAL_REQUIRED
    assert decision.allowed is False


def test_expired_authorization_blocks_outbound_reply() -> None:
    standing, repo = active_service()

    decision = standing.evaluate(
        channel_identity=CHANNEL,
        client_identity=CLIENT_A,
        action="faq_reply",
        now=NOW + timedelta(days=360),
    )

    assert decision.status == AutomationDecisionStatus.BLOCKED
    assert repo.get_authorization(CHANNEL).status == AuthorizationStatus.EXPIRED


def test_revoked_authorization_blocks_outbound_reply() -> None:
    standing, _ = active_service()
    standing.revoke(actor_id=OWNER, channel_identity=CHANNEL, now=NOW)

    decision = standing.evaluate(
        channel_identity=CHANNEL,
        client_identity=CLIENT_A,
        action="greeting",
        now=NOW,
    )

    assert decision.status == AutomationDecisionStatus.BLOCKED


def test_owner_manual_reply_pauses_ai_for_that_client() -> None:
    standing, _ = active_service()
    standing.record_owner_manual_reply(
        actor_id=OWNER,
        channel_identity=CHANNEL,
        client_identity=CLIENT_A,
        conversation_reference="conversation-1",
        now=NOW,
    )

    decision = standing.evaluate(
        channel_identity=CHANNEL,
        client_identity=CLIENT_A,
        action="faq_reply",
        now=NOW,
    )

    assert decision.status == AutomationDecisionStatus.PAUSED
    assert "manual takeover" in decision.reason.lower()


def test_manual_takeover_does_not_pause_another_client() -> None:
    standing, _ = active_service()
    standing.record_owner_manual_reply(
        actor_id=OWNER,
        channel_identity=CHANNEL,
        client_identity=CLIENT_A,
        now=NOW,
    )

    decision = standing.evaluate(
        channel_identity=CHANNEL,
        client_identity=CLIENT_B,
        action="faq_reply",
        now=NOW,
    )

    assert decision.allowed is True


def test_explicit_resume_restores_client_automation() -> None:
    standing, _ = active_service()
    standing.record_owner_manual_reply(
        actor_id=OWNER,
        channel_identity=CHANNEL,
        client_identity=CLIENT_A,
        now=NOW,
    )
    standing.resume_client(
        actor_id=OWNER,
        channel_identity=CHANNEL,
        client_identity=CLIENT_A,
        now=NOW + timedelta(minutes=1),
    )

    decision = standing.evaluate(
        channel_identity=CHANNEL,
        client_identity=CLIENT_A,
        action="faq_reply",
        now=NOW + timedelta(minutes=1),
    )

    assert decision.allowed is True


def test_global_pause_blocks_all_automatic_replies() -> None:
    standing, _ = active_service()
    standing.pause_global(actor_id=OWNER, channel_identity=CHANNEL, now=NOW)

    first = standing.evaluate(
        channel_identity=CHANNEL,
        client_identity=CLIENT_A,
        action="greeting",
        now=NOW,
    )
    second = standing.evaluate(
        channel_identity=CHANNEL,
        client_identity=CLIENT_B,
        action="faq_reply",
        now=NOW,
    )

    assert first.status == AutomationDecisionStatus.PAUSED
    assert second.status == AutomationDecisionStatus.PAUSED


def test_duplicate_webhook_is_ignored() -> None:
    standing, _ = active_service()

    first = standing.claim_webhook(
        channel_identity=CHANNEL,
        webhook_id="webhook-1",
        now=NOW,
    )
    second = standing.claim_webhook(
        channel_identity=CHANNEL,
        webhook_id="webhook-1",
        now=NOW,
    )

    assert first.status == AutomationDecisionStatus.ALLOWED
    assert second.status == AutomationDecisionStatus.DUPLICATE_IGNORED


def test_unauthorized_admin_cannot_change_authorization() -> None:
    standing, _ = service()

    with pytest.raises(WhatsAppAuthorizationError):
        standing.activate(
            actor_id="not-owner",
            channel_identity=CHANNEL,
            now=NOW,
        )


def test_sensitive_audit_metadata_is_redacted() -> None:
    standing, repo = service()

    authorization = standing.activate(
        actor_id=OWNER,
        channel_identity=CHANNEL,
        now=NOW,
        audit_metadata={
            "access_token": "must-not-appear",
            "phone": "919999999999",
            "purpose": "standing authorization",
        },
    )

    assert authorization.audit_metadata["access_token"] == "[REDACTED]"
    assert authorization.audit_metadata["phone"] == "[REDACTED]"
    assert "must-not-appear" not in str(authorization.audit_metadata)
    assert all(
        OWNER not in str(event) and CHANNEL not in str(event)
        for _, event in repo.audit_events
    )


def test_authorization_policy_has_no_sender_or_telegram_dependency() -> None:
    source = inspect.getsource(authorization_module)

    assert "WhatsAppService" not in source
    assert "TelegramService" not in source
    assert "requests." not in source


def test_delivery_attempts_are_idempotent_and_retry_bounded() -> None:
    standing, _ = active_service()

    for _ in range(3):
        decision = standing.begin_delivery_attempt(
            channel_identity=CHANNEL,
            client_identity=CLIENT_A,
            action="faq_reply",
            idempotency_key="delivery-1",
            now=NOW,
        )
        assert decision.status == AutomationDecisionStatus.ALLOWED
        standing.mark_delivery_failed(
            idempotency_key="delivery-1",
            error_category="timeout",
            now=NOW,
        )

    exhausted = standing.begin_delivery_attempt(
        channel_identity=CHANNEL,
        client_identity=CLIENT_A,
        action="faq_reply",
        idempotency_key="delivery-1",
        now=NOW,
    )
    assert exhausted.status == AutomationDecisionStatus.RETRY_EXHAUSTED


def test_duplicate_outbound_reservation_is_blocked() -> None:
    standing, _ = active_service()

    first = standing.begin_delivery_attempt(
        channel_identity=CHANNEL,
        client_identity=CLIENT_A,
        action="faq_reply",
        idempotency_key="delivery-in-flight",
        now=NOW,
    )
    duplicate = standing.begin_delivery_attempt(
        channel_identity=CHANNEL,
        client_identity=CLIENT_A,
        action="faq_reply",
        idempotency_key="delivery-in-flight",
        now=NOW,
    )

    assert first.status == AutomationDecisionStatus.ALLOWED
    assert duplicate.status == AutomationDecisionStatus.DUPLICATE_IGNORED


def test_per_client_rate_limit_is_enforced() -> None:
    standing, _ = service(delivery_limit=1)
    standing.activate(actor_id=OWNER, channel_identity=CHANNEL, now=NOW)

    first = standing.begin_delivery_attempt(
        channel_identity=CHANNEL,
        client_identity=CLIENT_A,
        action="faq_reply",
        idempotency_key="delivery-a",
        now=NOW,
    )
    second = standing.begin_delivery_attempt(
        channel_identity=CHANNEL,
        client_identity=CLIENT_A,
        action="faq_reply",
        idempotency_key="delivery-b",
        now=NOW,
    )

    assert first.status == AutomationDecisionStatus.ALLOWED
    assert second.status == AutomationDecisionStatus.RATE_LIMITED


def test_daily_report_warns_before_expiry_without_personal_identifiers() -> None:
    standing, _ = active_service()

    report = standing.build_daily_owner_report(
        channel_identity=CHANNEL,
        now=NOW + timedelta(days=340),
    )

    assert report.expiry_warning is True
    assert CHANNEL not in report.channel_fingerprint
