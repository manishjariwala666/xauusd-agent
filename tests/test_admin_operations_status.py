from contextlib import contextmanager

from services import admin_operations_status as status_module


class _RowsResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return self

    def all(self):
        return self._rows


class _Session:
    def __init__(self, rows):
        self._rows = rows

    def execute(self, _statement):
        return _RowsResult(self._rows)


def _session_scope_for(rows):
    @contextmanager
    def _scope():
        yield _Session(rows)

    return _scope


def test_delivery_summary_exposes_retry_truth_without_recipient_identity(monkeypatch):
    rows = [
        {
            "signal_id": 10,
            "channel": "telegram",
            "recipient_hash": "a" * 64,
            "attempts": 1,
            "sent_at": object(),
            "error_category": None,
        },
        {
            "signal_id": 10,
            "channel": "whatsapp",
            "recipient_hash": "b" * 64,
            "attempts": 2,
            "sent_at": None,
            "error_category": "TimeoutError",
        },
    ]
    monkeypatch.setattr(
        status_module,
        "session_scope",
        _session_scope_for(rows),
    )

    result = status_module._delivery_summary()

    assert result["available"] is True
    assert result["max_attempts"] == 3
    assert result["stale_claim_minutes"] == 5
    assert result["channels"]["telegram"]["sent"] == 1
    assert result["channels"]["whatsapp"]["failed"] == 1
    assert result["failed_recipients"][0]["recipient"] == "b" * 12
    assert len(result["failed_recipients"][0]["recipient"]) == 12


def test_content_summary_reports_verified_draft_word_count(monkeypatch):
    rows = [
        {
            "id": 21,
            "title": "Gold discipline",
            "body": "<h1>Gold discipline</h1><p>one two three four</p>",
            "image_url": "",
            "is_published": False,
            "published_at": None,
            "updated_at": None,
        }
    ]
    monkeypatch.setattr(
        status_module,
        "session_scope",
        _session_scope_for(rows),
    )

    result = status_module._content_summary()

    assert result["available"] is True
    assert result["drafts"] == 1
    assert result["published"] == 0
    assert result["automatic_publish"] is False
    assert result["items"][0]["status"] == "DRAFT"
    assert result["items"][0]["word_count"] == 6


def test_operations_payload_keeps_all_external_actions_locked(monkeypatch):
    monkeypatch.setattr(
        status_module,
        "_agent_summary",
        lambda: {"available": True, "count": 7, "enabled": 6, "errors": 0},
    )
    monkeypatch.setattr(
        status_module,
        "_run_summary",
        lambda: {"available": True, "items": []},
    )
    monkeypatch.setattr(
        status_module,
        "_captain_summary",
        lambda: {"available": False, "reason": "audit unavailable"},
    )
    monkeypatch.setattr(
        status_module,
        "_content_summary",
        lambda: {"available": True, "items": [], "drafts": 0, "published": 0, "automatic_publish": False},
    )
    monkeypatch.setattr(
        status_module,
        "_delivery_summary",
        lambda: {"available": False, "channels": {}, "failed_recipients": [], "max_attempts": 3, "stale_claim_minutes": 5},
    )

    result = status_module.get_admin_operations_status()

    assert result["read_only"] is True
    assert result["master_ai"]["shared_backend"] == "generate_master_ai_reply"
    assert result["master_ai"]["interfaces"] == ["ADMIN", "TELEGRAM"]
    assert result["safety"]["publishing"] == "OWNER_APPROVAL_REQUIRED"
    assert result["safety"]["production_deployment"] == "OWNER_APPROVAL_REQUIRED"
    assert result["safety"]["database_migration"] == "EXPLICIT_OWNER_APPROVAL_REQUIRED"
    assert result["safety"]["trade_execution"] == "FORBIDDEN"
    assert result["safety"]["automatic_content_publish"] is False
