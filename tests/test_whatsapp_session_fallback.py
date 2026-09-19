from datetime import datetime, timezone
from types import SimpleNamespace

import scripts.run_whatsapp_session_fallback as fallback
from services.session_signal_broadcast import SessionSetup, _delivery_key


def test_fallback_uses_same_dedupe_key_as_primary_delivery():
    recipient = "120363000000000000@g.us"
    setup = SessionSetup(
        signal_date="2026-09-21",
        session_name="morning",
        direction="BUY",
        entry=1,
        stop_loss=1,
        targets=(1, 2, 3, 4, 5, 6),
    )

    assert fallback._dedupe_key(
        setup.signal_date,
        setup.session_name,
        setup.direction,
        recipient,
    ) == _delivery_key(setup, recipient)


def test_no_due_setups_returns_without_database_or_whatsapp(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "not-a-valid-sqlalchemy-url")

    fake_sheets = object()
    monkeypatch.setattr(fallback, "GoogleSheetsService", lambda: fake_sheets)
    monkeypatch.setattr(
        fallback,
        "load_due_session_setups",
        lambda sheets, now: [],
    )

    def unexpected(*args, **kwargs):
        raise AssertionError("No DB/Supabase/WhatsApp client should be created")

    monkeypatch.setattr(fallback, "create_client", unexpected)
    monkeypatch.setattr(fallback, "WhatsAppService", unexpected)

    assert fallback.run() == (0, 0)
