from __future__ import annotations

from datetime import datetime, timezone
import asyncio
import hashlib
import hmac
import json
from types import SimpleNamespace
from typing import Any

import pytest

import backend
from services import conversation_service, production_agents
from services import whatsapp_standing_authorization_repository as pg_repository
from services.whatsapp_standing_authorization import (
    AutomationDecisionStatus,
    InMemoryStandingAuthorizationRepository,
    WhatsAppStandingAuthorizationService,
)


CHANNEL = "verified-business-account"
CLIENT_A = "client-a"
CLIENT_B = "client-b"
OWNER = "7"


def _active_service() -> WhatsAppStandingAuthorizationService:
    service = WhatsAppStandingAuthorizationService(
        InMemoryStandingAuthorizationRepository(),
        owner_authorizer=lambda actor_id: actor_id == OWNER,
    )
    service.activate(
        actor_id=OWNER,
        channel_identity=CHANNEL,
        now=datetime.now(timezone.utc),
    )
    return service


class _ScalarResult:
    def __init__(self, value: Any) -> None:
        self.value = value

    def scalar_one(self) -> Any:
        return self.value

    def scalar_one_or_none(self) -> Any:
        return self.value


class _InboundSession:
    def __init__(self, inserted: int | None = 100) -> None:
        self.inserted = inserted
        self.message_was_stored = False

    def execute(self, statement: Any, parameters: Any = None) -> _ScalarResult:
        sql = str(statement)
        if "INSERT INTO public.ai_conversations" in sql:
            return _ScalarResult(42)
        if "INSERT INTO public.ai_messages" in sql:
            self.message_was_stored = True
            return _ScalarResult(self.inserted)
        raise AssertionError(sql)


class _Scope:
    def __init__(self, session: Any) -> None:
        self.session = session

    def __enter__(self) -> Any:
        return self.session

    def __exit__(self, *_: Any) -> bool:
        return False


def _enable_inbound_test(
    monkeypatch: pytest.MonkeyPatch, session: _InboundSession
) -> None:
    monkeypatch.setattr(
        conversation_service, "session_scope", lambda: _Scope(session)
    )
    monkeypatch.setattr(
        conversation_service, "append_message_log", lambda **_: None
    )
    monkeypatch.setattr(
        conversation_service, "_auto_reply_agents_enabled", lambda: True
    )


def test_active_authorization_allows_enqueue(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _InboundSession()
    _enable_inbound_test(monkeypatch, session)
    queued: list[tuple[str, dict[str, Any]]] = []

    conversation_service.record_inbound_message(
        channel="WHATSAPP",
        external_user_id=CLIENT_A,
        external_message_id="wamid-1",
        body="Hello, service details please",
        channel_identity=CHANNEL,
        authorization_service=_active_service(),
        enqueue_job=lambda key, payload: queued.append((key, payload)) or 1,
    )

    assert session.message_was_stored
    assert queued[0][0] == "whatsapp_reply_agent"
    assert queued[0][1]["automation_action"] == "greeting"
    assert queued[0][1]["channel_identity"] == CHANNEL


def test_whatsapp_sheet_log_contains_no_raw_phone_or_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _InboundSession()
    monkeypatch.setattr(
        conversation_service, "session_scope", lambda: _Scope(session)
    )
    monkeypatch.setattr(
        conversation_service, "_auto_reply_agents_enabled", lambda: False
    )
    logs: list[dict[str, Any]] = []
    monkeypatch.setattr(
        conversation_service,
        "append_message_log",
        lambda **kwargs: logs.append(kwargs),
    )
    raw_phone = "919999999999"
    raw_message = "My private support request"

    conversation_service.record_inbound_message(
        channel="WHATSAPP",
        external_user_id=raw_phone,
        external_message_id="wamid-private",
        body=raw_message,
        channel_identity=CHANNEL,
    )

    assert raw_phone not in str(logs)
    assert raw_message not in str(logs)
    assert str(logs[0]["phone"]).startswith("wa_")


@pytest.mark.parametrize("state", ["expired", "revoked", "paused"])
def test_inactive_authorization_blocks_enqueue_but_stores_inbound(
    monkeypatch: pytest.MonkeyPatch, state: str
) -> None:
    session = _InboundSession()
    _enable_inbound_test(monkeypatch, session)
    standing = _active_service()
    if state == "expired":
        authorization = standing.repository.get_authorization(CHANNEL)
        standing.repository.save_authorization(
            __import__("dataclasses").replace(
                authorization,
                valid_until=datetime(2020, 1, 1, tzinfo=timezone.utc),
            )
        )
    elif state == "revoked":
        standing.revoke(actor_id=OWNER, channel_identity=CHANNEL)
    else:
        standing.pause_global(actor_id=OWNER, channel_identity=CHANNEL)
    queued: list[object] = []

    conversation_service.record_inbound_message(
        channel="WHATSAPP",
        external_user_id=CLIENT_A,
        external_message_id=f"wamid-{state}",
        body="Hello",
        channel_identity=CHANNEL,
        authorization_service=standing,
        enqueue_job=lambda *args, **kwargs: queued.append((args, kwargs)) or 1,
    )

    assert session.message_was_stored
    assert queued == []


def test_missing_repository_fails_closed_after_storage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _InboundSession()
    _enable_inbound_test(monkeypatch, session)
    queued: list[object] = []
    monkeypatch.setattr(
        conversation_service,
        "_whatsapp_authorization_service",
        lambda: (_ for _ in ()).throw(RuntimeError("schema unavailable")),
    )

    conversation_service.record_inbound_message(
        channel="WHATSAPP",
        external_user_id=CLIENT_A,
        external_message_id="wamid-missing",
        body="Hello",
        channel_identity=CHANNEL,
        enqueue_job=lambda *args, **kwargs: queued.append((args, kwargs)) or 1,
    )

    assert session.message_was_stored
    assert queued == []


def test_high_risk_inbound_requires_approval_and_is_not_queued(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _InboundSession()
    _enable_inbound_test(monkeypatch, session)
    queued: list[object] = []

    conversation_service.record_inbound_message(
        channel="WHATSAPP",
        external_user_id=CLIENT_A,
        external_message_id="wamid-refund",
        body="Please guarantee my refund now",
        channel_identity=CHANNEL,
        authorization_service=_active_service(),
        enqueue_job=lambda *args, **kwargs: queued.append((args, kwargs)) or 1,
    )

    assert session.message_was_stored
    assert queued == []


def test_verified_webhook_channel_identity_reaches_conversation_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "test-only-signing-secret"
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": CHANNEL},
                            "messages": [
                                {
                                    "from": CLIENT_A,
                                    "id": "wamid-route",
                                    "type": "text",
                                    "text": {"body": "Hello"},
                                }
                            ],
                        }
                    }
                ]
            }
        ]
    }
    raw = json.dumps(payload).encode()
    signature = "sha256=" + hmac.new(
        secret.encode(), raw, hashlib.sha256
    ).hexdigest()
    received: list[dict[str, Any]] = []

    class _Request:
        async def body(self) -> bytes:
            return raw

    monkeypatch.setattr(
        backend, "get_settings", lambda: SimpleNamespace(meta_app_secret=secret)
    )
    monkeypatch.setattr(
        backend,
        "record_inbound_message",
        lambda **kwargs: received.append(kwargs) or (42, True),
    )

    result = asyncio.run(
        backend.whatsapp_webhook(
            _Request(), x_hub_signature_256=signature
        )
    )

    assert result == {"status": "accepted"}
    assert received[0]["channel_identity"] == CHANNEL


class _Mappings:
    def __init__(self, row: Any = None, rows: list[Any] | None = None) -> None:
        self.row = row
        self.rows = rows or []

    def first(self) -> Any:
        return self.row

    def one(self) -> Any:
        return self.row

    def all(self) -> list[Any]:
        return self.rows


class _ReplyResult:
    def __init__(self, row: Any = None, rows: list[Any] | None = None) -> None:
        self.row = row
        self.rows = rows

    def mappings(self) -> _Mappings:
        return _Mappings(self.row, self.rows)


class _ReplySession:
    def __init__(self, channel: str = "WHATSAPP") -> None:
        self.channel = channel

    def execute(self, statement: Any, parameters: Any = None) -> _ReplyResult:
        sql = str(statement)
        if "SELECT id, external_user_id, human_takeover_until" in sql:
            return _ReplyResult(
                {
                    "id": 42,
                    "external_user_id": CLIENT_A,
                    "human_takeover_until": None,
                }
            )
        if "SELECT sender_type, body" in sql:
            return _ReplyResult(
                rows=[{"sender_type": "USER", "body": "Hello"}]
            )
        if "SELECT channel, external_user_id" in sql:
            return _ReplyResult(
                {"channel": self.channel, "external_user_id": CLIENT_A}
            )
        if "INSERT INTO public.ai_messages" in sql or "UPDATE public.ai_conversations" in sql:
            return _ReplyResult()
        raise AssertionError(sql)


class _FakeAI:
    def __init__(self, before_reply: Any = None) -> None:
        self.before_reply = before_reply

    def generate_json(self, **_: Any) -> dict[str, str]:
        if self.before_reply:
            self.before_reply()
        return {"reply": "Safe routine reply"}


class _NoSendWhatsApp:
    def send_text(self, *_: Any) -> str:
        raise AssertionError("sender must not run after authorization changes")


def test_authorization_is_rechecked_immediately_before_sender(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    standing = _active_service()
    monkeypatch.setattr(
        production_agents, "session_scope", lambda: _Scope(_ReplySession())
    )
    monkeypatch.setattr(
        production_agents, "_whatsapp_authorization_service", lambda: standing
    )
    monkeypatch.setattr(
        production_agents,
        "AIProvider",
        lambda: _FakeAI(
            lambda: standing.pause_global(
                actor_id=OWNER, channel_identity=CHANNEL
            )
        ),
    )
    monkeypatch.setattr(
        production_agents, "WhatsAppService", lambda: _NoSendWhatsApp()
    )

    with pytest.raises(
        production_agents.WhatsAppAutomationBlocked, match="PAUSED:"
    ):
        production_agents.run_whatsapp_reply_agent(
            {
                "conversation_id": 42,
                "channel_identity": CHANNEL,
                "client_identity": CLIENT_A,
                "automation_action": "faq_reply",
                "delivery_idempotency_key": "delivery-recheck",
            }
        )


def test_high_risk_outbound_never_calls_sender(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    standing = _active_service()
    monkeypatch.setattr(
        production_agents, "session_scope", lambda: _Scope(_ReplySession())
    )
    monkeypatch.setattr(
        production_agents, "_whatsapp_authorization_service", lambda: standing
    )
    monkeypatch.setattr(
        production_agents, "AIProvider", lambda: _FakeAI()
    )
    monkeypatch.setattr(
        production_agents, "WhatsAppService", lambda: _NoSendWhatsApp()
    )

    with pytest.raises(
        production_agents.WhatsAppAutomationBlocked,
        match="APPROVAL_REQUIRED:",
    ):
        production_agents.run_whatsapp_reply_agent(
            {
                "conversation_id": 42,
                "channel_identity": CHANNEL,
                "client_identity": CLIENT_A,
                "automation_action": "payment_commitment",
                "delivery_idempotency_key": "delivery-high-risk",
            }
        )


class _FakeWhatsApp:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def send_text(self, recipient: str, message: str) -> str:
        self.calls.append((recipient, message))
        return "wamid-human"


def test_manual_admin_reply_pauses_only_that_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    standing = _active_service()
    sender = _FakeWhatsApp()
    monkeypatch.setattr(
        conversation_service, "session_scope", lambda: _Scope(_ReplySession())
    )
    monkeypatch.setattr(
        conversation_service, "WhatsAppService", lambda: sender
    )
    monkeypatch.setattr(
        conversation_service, "append_message_log", lambda **_: None
    )

    conversation_service.send_human_reply(
        42,
        7,
        "I will handle this conversation.",
        authorization_service=standing,
        channel_identity=CHANNEL,
    )

    paused = standing.evaluate(
        channel_identity=CHANNEL,
        client_identity=CLIENT_A,
        action="faq_reply",
    )
    other = standing.evaluate(
        channel_identity=CHANNEL,
        client_identity=CLIENT_B,
        action="faq_reply",
    )
    assert paused.status == AutomationDecisionStatus.PAUSED
    assert other.allowed
    assert len(sender.calls) == 1


def test_direct_owner_hook_requires_verified_server_mapping() -> None:
    with pytest.raises(PermissionError):
        conversation_service.record_verified_owner_whatsapp_reply(
            provider_owner_identity="provider-actor",
            channel_identity=CHANNEL,
            client_identity=CLIENT_A,
            conversation_reference="42",
            resolve_verified_admin=lambda *_: None,
            authorization_service=_active_service(),
        )


class _RepositoryResult:
    def __init__(self, *, scalar: Any = None, row: Any = None) -> None:
        self.scalar = scalar
        self.row = row

    def scalar_one(self) -> Any:
        return self.scalar

    def mappings(self) -> _Mappings:
        return _Mappings(self.row)


class _RepositorySession:
    def __init__(self) -> None:
        self.sql: list[str] = []

    def execute(self, statement: Any, parameters: Any = None) -> _RepositoryResult:
        sql = str(statement)
        self.sql.append(sql)
        if "pg_advisory_xact_lock" in sql:
            return _RepositoryResult(scalar=None)
        if "SELECT attempts, delivered, in_flight" in sql:
            return _RepositoryResult(row=None)
        if "INSERT INTO public.whatsapp_delivery_attempts" in sql:
            return _RepositoryResult()
        if "SELECT COUNT(*)" in sql:
            return _RepositoryResult(scalar=1)
        raise AssertionError(sql)


def test_postgres_reservation_locks_missing_row_and_rate_count_is_exact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _RepositorySession()
    monkeypatch.setattr(
        pg_repository, "session_scope", lambda: _Scope(session)
    )
    repository = pg_repository.PostgresStandingAuthorizationRepository()

    status, state = repository.reserve_delivery_attempt(
        idempotency_key="delivery-atomic",
        channel_fingerprint="channel-hash",
        client_fingerprint="client-hash",
        attempted_at=datetime.now(timezone.utc),
        max_attempts=3,
    )
    count = repository.register_client_delivery(
        CHANNEL, CLIENT_A, datetime.now(timezone.utc)
    )

    assert status == "reserved"
    assert state is not None and state.attempts == 1
    assert "pg_advisory_xact_lock" in session.sql[0]
    assert count == 1
