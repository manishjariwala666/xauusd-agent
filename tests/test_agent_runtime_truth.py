from services.admin_agents_api import _decorate_agent_item
from services.master_ai_agent_registry import get_agent_dashboard_record, list_registered_agents
from services.master_ai_approval_bridge import queue_master_ai_owner_approval


def _record(agent_key: str):
    agent = next(agent for agent in list_registered_agents() if agent.agent_key == agent_key)
    return get_agent_dashboard_record(agent)


def test_runtime_kind_distinguishes_scheduled_native_and_embedded_agents():
    signal = _decorate_agent_item(_record("signal_agent"), live_by_key={})
    assert signal["runtime_kind"] == "SCHEDULED_WORKER"
    assert signal["is_configured"] is False
    assert signal["status"] == "NOT_CONFIGURED"

    market = _decorate_agent_item(_record("market_data_agent"), live_by_key={})
    assert market["runtime_kind"] == "MASTER_AI_NATIVE"
    assert market["is_configured"] is True
    assert market["is_enabled"] is True

    macro = _decorate_agent_item(_record("macro_ai_agent"), live_by_key={})
    assert macro["runtime_kind"] == "EMBEDDED"
    assert macro["is_configured"] is True
    assert macro["status"] == "READY_READ_ONLY"


def test_native_db_row_enabled_state_becomes_authoritative():
    market = _decorate_agent_item(
        _record("market_data_agent"),
        live_by_key={
            "market_data_agent": {
                "agent_key": "market_data_agent",
                "is_enabled": False,
                "status": "IDLE",
            }
        },
    )
    assert market["runtime_kind"] == "MASTER_AI_NATIVE"
    assert market["worker_configured"] is True
    assert market["is_enabled"] is False
    assert market["status"] == "IDLE"


def test_owner_approval_bridge_queues_without_execution_payload(monkeypatch):
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return {"id": 44, "status": "PENDING"}

    monkeypatch.setattr(
        "services.master_ai_approval_bridge.create_or_refresh_agent_approval",
        fake_create,
    )
    queued = queue_master_ai_owner_approval(
        action="run_seo_agent",
        agent_key="seo_agent",
        reason="SEO persistence requires approval.",
    )
    assert queued.queued is True
    assert queued.approval_id == 44
    assert queued.status == "PENDING"
    assert captured["action_key"] == "run_seo_agent"
    assert captured["agent_key"] == "seo_agent"
    assert captured["request_payload"]["execution_requested"] is False
    assert "request_text" not in captured["request_payload"]


def test_owner_approval_bridge_fails_closed_when_store_unavailable(monkeypatch):
    def fail(**kwargs):
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(
        "services.master_ai_approval_bridge.create_or_refresh_agent_approval",
        fail,
    )
    queued = queue_master_ai_owner_approval(
        action="run_signal_agent",
        agent_key="signal_agent",
        reason="approval required",
    )
    assert queued.queued is False
    assert queued.approval_id is None
