from __future__ import annotations

from fastapi import Response

from services import admin_agents_api


def test_agent_list_uses_registry_when_local_preview_database_is_unavailable(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        admin_agents_api,
        "_identity",
        lambda authorization, secret: object(),
    )
    monkeypatch.setattr(
        admin_agents_api,
        "local_admin_preview_enabled",
        lambda: True,
    )
    monkeypatch.setattr(
        admin_agents_api,
        "list_ai_agents",
        lambda: (_ for _ in ()).throw(
            RuntimeError("database unavailable")
        ),
    )

    result = admin_agents_api.admin_agent_list(
        response=Response(),
        authorization="Bearer test",
        x_admin_bff_key="test",
    )

    assert result["read_only"] is True
    assert result["count"] >= 18
    assert any(
        item["agent_key"] == "market_data_agent"
        for item in result["items"]
    )
    assert all(
        item["status"] == "NOT_CONFIGURED"
        for item in result["items"]
    )
