"""Focused tests for the protected read-only Agent Dashboard API."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.admin_agents_api import router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_agent_list_requires_admin_authentication() -> None:
    response = _client().get("/admin/agents")

    assert response.status_code in {401, 403, 503}


def test_agent_list_returns_safe_read_only_records(monkeypatch) -> None:
    monkeypatch.setattr(
        "services.admin_agents_api._identity",
        lambda authorization, secret: object(),
    )
    monkeypatch.setattr(
        "services.admin_agents_api.list_ai_agents",
        lambda: [
            {
                "agent_key": "signal_agent",
                "is_enabled": False,
                "status": "IDLE",
                "last_run_at": "2026-07-31T06:00:00+00:00",
                "last_error": "",
                "schedule_minutes": 15,
                "next_scheduled_run_at": None,
                "success_count": 8,
                "failure_count": 1,
                "queue_size": 0,
                "last_duration_ms": 245,
            }
        ],
    )

    response = _client().get("/admin/agents")

    assert response.status_code == 200
    payload = response.json()

    assert payload["count"] == len(payload["items"])
    assert payload["read_only"] is True
    assert len(payload["items"]) == payload["count"]
    assert response.headers["cache-control"] == "private, no-store"

    signal = next(
        item
        for item in payload["items"]
        if item["agent_key"] == "signal_agent"
    )

    assert signal["brain_configured"] is True
    assert signal["default_risk"] == "HIGH"
    assert "execute_trade" in signal["forbidden_actions"]
    assert signal["is_configured"] is True
    assert signal["is_enabled"] is False
    assert signal["status"] == "IDLE"
    assert signal["schedule_minutes"] == 15
    assert signal["success_count"] == 8
    assert signal["failure_count"] == 1
    assert signal["queue_size"] == 0
    assert signal["last_duration_ms"] == 245

    report = next(
        item
        for item in payload["items"]
        if item["agent_key"] == "report_agent"
    )
    assert report["is_configured"] is False
    assert report["is_enabled"] is None
    assert report["status"] == "NOT_CONFIGURED"


def test_agent_detail_returns_one_registered_agent(monkeypatch) -> None:
    monkeypatch.setattr(
        "services.admin_agents_api._identity",
        lambda authorization, secret: object(),
    )

    response = _client().get("/admin/agents/report_agent")

    assert response.status_code == 200
    payload = response.json()

    assert payload["found"] is True
    assert payload["read_only"] is True
    assert payload["item"]["agent_key"] == "report_agent"
    assert payload["item"]["default_risk"] == "READ_ONLY"


def test_unknown_agent_returns_safe_not_found_payload(monkeypatch) -> None:
    monkeypatch.setattr(
        "services.admin_agents_api._identity",
        lambda authorization, secret: object(),
    )

    response = _client().get("/admin/agents/not_real")

    assert response.status_code == 200
    assert response.json() == {
        "item": None,
        "found": False,
        "read_only": True,
    }


def test_agent_api_does_not_expose_sensitive_field_names(monkeypatch) -> None:
    monkeypatch.setattr(
        "services.admin_agents_api._identity",
        lambda authorization, secret: object(),
    )
    monkeypatch.setattr(
        "services.admin_agents_api.list_ai_agents",
        lambda: [],
    )

    payload = _client().get("/admin/agents").json()

    forbidden_fields = {
        "token",
        "secret",
        "password",
        "credential",
        "database_url",
        "api_key",
    }

    for item in payload["items"]:
        assert forbidden_fields.isdisjoint(item)


def test_agent_builder_preview_requires_authentication() -> None:
    response = _client().post(
        "/admin/agents/builder/preview",
        json={
            "display_name": "Social Media Agent",
            "department": "marketing",
            "purpose": (
                "Prepare platform-specific social media drafts "
                "for approved published content."
            ),
        },
    )

    assert response.status_code in {401, 403}


def test_agent_builder_preview_returns_locked_brain(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "services.admin_agents_api._identity",
        lambda *_: object(),
    )

    response = _client().post(
        "/admin/agents/builder/preview",
        json={
            "display_name": "Social Media Agent",
            "department": "marketing",
            "purpose": (
                "Prepare platform-specific social media drafts "
                "for approved published content."
            ),
            "requested_actions": [
                "publish_social_post",
            ],
        },
    )

    assert response.status_code == 200

    payload = response.json()
    preview = payload["preview"]

    assert preview["state"] == "BRAIN_PREVIEW"
    assert preview["agent_key"] == "social_media_agent"
    assert preview["default_risk"] == "HIGH"
    assert preview["execution_enabled"] is False
    assert payload["preview_only"] is True
    assert payload["registry_written"] is False
    assert payload["runner_written"] is False
    assert payload["files_generated"] is False


def test_agent_builder_preview_rejects_invalid_spec(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "services.admin_agents_api._identity",
        lambda *_: object(),
    )

    response = _client().post(
        "/admin/agents/builder/preview",
        json={
            "display_name": "Invalid Agent",
            "purpose": "Too short",
        },
    )

    assert response.status_code == 422
    assert "purpose" in response.json()["detail"].lower()
