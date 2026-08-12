"""Phase 4A lifecycle tests against explicitly configured isolated PostgreSQL."""

import os

import pytest
from sqlalchemy import create_engine, text

from services import admin_signals_service
from services.admin_signals_api import SignalPayload


DATABASE_URL = os.getenv("TEST_ADMIN_DATABASE_URL", "").strip()
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="isolated PostgreSQL is required")


@pytest.fixture(autouse=True)
def isolated_scope(monkeypatch: pytest.MonkeyPatch):
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    from contextlib import contextmanager
    from sqlalchemy.orm import sessionmaker
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    @contextmanager
    def scope():
        session = factory()
        try:
            yield session; session.commit()
        except Exception:
            session.rollback(); raise
        finally: session.close()

    monkeypatch.setattr(admin_signals_service, "session_scope", scope)
    yield engine
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM market_signals WHERE source='ADMIN' AND analysis_summary LIKE 'Phase 4A integration:%'"))
        connection.execute(text("DELETE FROM admin_auth_audit_events WHERE request_id LIKE 'phase4a-integration-%'"))
    engine.dispose()


def payload(direction="BUY"):
    levels = {"entry_price": "2350.125000", "stop_loss": "2340", "target_1": "2360", "target_2": "2370"} if direction == "BUY" else {"entry_price": "2350.125000", "stop_loss": "2360", "target_1": "2340", "target_2": "2330"}
    return SignalPayload(symbol="XAUUSD", direction=direction, analysis_summary=f"Phase 4A integration: {direction} synthetic signal.", technical_reason="Synthetic integration context.", risk_note="Local test only.", **levels).model_dump()


def test_create_publish_public_exclusion_transition_trash_restore_delete(isolated_scope) -> None:
    draft = admin_signals_service.create_admin_signal(actor_id=1, request_id="phase4a-integration-create", values=payload())
    assert draft["lifecycle_status"] == "DRAFT"
    with pytest.raises(admin_signals_service.SignalNotFoundError):
        admin_signals_service.get_public_signal(str(draft["public_id"]))
    published = admin_signals_service.transition_admin_signal(signal_id=draft["id"], action="PUBLISH", actor_id=1, request_id="phase4a-integration-publish")
    assert published["publication_status"] == "PUBLISHED"
    public = admin_signals_service.get_public_signal(str(published["public_id"]))
    assert "created_by" not in public and "id" not in public
    active = admin_signals_service.transition_admin_signal(signal_id=draft["id"], action="ACTIVATE", actor_id=1, request_id="phase4a-integration-activate")
    assert active["lifecycle_status"] == "ACTIVE"
    with pytest.raises(admin_signals_service.SignalConflictError):
        admin_signals_service.transition_admin_signal(signal_id=draft["id"], action="TRASH", actor_id=1, request_id="phase4a-integration-invalid")
    closed = admin_signals_service.transition_admin_signal(signal_id=draft["id"], action="CLOSE", actor_id=1, request_id="phase4a-integration-close", outcome="MANUALLY_VERIFIED", result_points=None)
    assert closed["lifecycle_status"] == "CLOSED"
    trashed = admin_signals_service.transition_admin_signal(signal_id=draft["id"], action="TRASH", actor_id=1, request_id="phase4a-integration-trash")
    assert trashed["deleted_at"] is not None
    restored = admin_signals_service.transition_admin_signal(signal_id=draft["id"], action="RESTORE", actor_id=1, request_id="phase4a-integration-restore")
    assert restored["lifecycle_status"] == "DRAFT"
    trashed = admin_signals_service.transition_admin_signal(signal_id=draft["id"], action="TRASH", actor_id=1, request_id="phase4a-integration-trash2")
    assert admin_signals_service.delete_admin_signal(signal_id=draft["id"], actor_id=1, request_id="phase4a-integration-delete", confirmed=True) == {"deleted": True}


def test_search_filters_pagination_duplicate_and_audit(isolated_scope) -> None:
    buy = admin_signals_service.create_admin_signal(actor_id=1, request_id="phase4a-integration-buy", values=payload("BUY"))
    admin_signals_service.create_admin_signal(actor_id=1, request_id="phase4a-integration-sell", values=payload("SELL"))
    duplicate = admin_signals_service.duplicate_admin_signal(signal_id=buy["id"], actor_id=1, request_id="phase4a-integration-duplicate")
    assert duplicate["lifecycle_status"] == "DRAFT" and duplicate["id"] != buy["id"]
    listed = admin_signals_service.list_admin_signals(page=1, page_size=1, search="integration", direction="BUY")
    assert listed["total"] == 2 and listed["pages"] == 2
    assert admin_signals_service.list_admin_signals(page=1, page_size=10, date_filter="7d")["total"] >= 3
    with isolated_scope.connect() as connection:
        events = set(connection.execute(text("SELECT event_type FROM admin_auth_audit_events WHERE request_id LIKE 'phase4a-integration-%'")).scalars())
    assert {"SIGNAL_CREATED", "SIGNAL_DUPLICATED"}.issubset(events)
