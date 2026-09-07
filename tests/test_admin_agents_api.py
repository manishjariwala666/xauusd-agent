"""Focused tests for the protected admin agents API and route wiring."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend import app
from services.admin_auth_service import AdminIdentity

client = TestClient(app)


def test_admin_agents_routes_are_registered() -> None:
    paths = app.openapi()["paths"]
    assert "get" in paths["/admin/agents"]
    assert "get" in paths["/admin/agents/runs"]
    assert "post" in paths["/admin/agents/{agent_key}/enable"]
    assert "post" in paths["/admin/agents/{agent_key}/disable"]


def test_admin_agents_list_and_runs_require_admin_auth(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        "services.admin_agents_api.verify_bff_secret",
        lambda _: None,
    )
    monkeypatch.setattr(
        "services.admin_agents_api.validate_admin_session",
        lambda token: AdminIdentity(user_id=1, email="admin@example.com", role="ADMIN"),
    )
    monkeypatch.setattr(
        "services.admin_agents_api.list_ai_agents",
        lambda: [
            {
                "agent_key": "seo_agent",
                "display_name": "SEO Agent",
                "is_enabled": False,
                "status": "ERROR",
                "last_run_at": None,
                "last_error": "Missing API key",
                "success_count": 0,
                "failure_count": 1,
                "queue_size": 0,
                "next_scheduled_run_at": None,
            }
        ],
    )
    monkeypatch.setattr(
        "services.admin_agents_api.list_agent_runs",
        lambda limit=10: [
            {
                "id": 1,
                "agent_key": "seo_agent",
                "display_name": "SEO Agent",
                "status": "ERROR",
                "error_message": "Missing API key",
            }
        ],
    )

    response = client.get(
        "/admin/agents",
        headers={
            "Authorization": "Bearer test-token",
            "x-admin-bff-key": "bff-secret",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["agents"][0]["agent_key"] == "seo_agent"
    assert payload["runs"][0]["agent_key"] == "seo_agent"


def test_enable_disable_agent_route_updates_state(monkeypatch: Any) -> None:
    calls: list[tuple[str, bool]] = []

    monkeypatch.setattr(
        "services.admin_agents_api.verify_bff_secret",
        lambda _: None,
    )
    monkeypatch.setattr(
        "services.admin_agents_api.validate_admin_session",
        lambda token: AdminIdentity(user_id=1, email="admin@example.com", role="ADMIN"),
    )

    def fake_set(agent_key: str, enabled: bool) -> None:
        calls.append((agent_key, enabled))

    monkeypatch.setattr("services.admin_agents_api.set_ai_agent_enabled", fake_set)

    response = client.post(
        "/admin/agents/seo_agent/disable",
        headers={
            "Authorization": "Bearer test-token",
            "x-admin-bff-key": "bff-secret",
        },
    )
    assert response.status_code == 200
    assert calls == [("seo_agent", False)]
