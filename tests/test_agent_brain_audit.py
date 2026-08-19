from types import SimpleNamespace

import pytest

from services.agent_brain_registry import get_agent_brain
from services.execution_planner import AgentDescriptor, ExecutionPlanner
from services.master_ai_access_policy import ApprovalLevel, get_action_policy
from services.master_ai_agent_registry import list_registered_agents
from services.master_ai_capability_matrix import CapabilityMode, get_agent_capability
from services.master_ai_intent_resolver import resolve_master_ai_intent
from services.master_ai_tool_router import TASKS, execute_master_ai_action
from services.production_agents import RUNNERS
from services.worker_agent_adapter import ORCHESTRATION_NATIVE_AGENT_KEYS, WorkerAgentAdapter


def test_every_registered_agent_has_brain_and_capability():
    agents = list_registered_agents()
    assert len(agents) >= 22
    assert len({agent.agent_key for agent in agents}) == len(agents)
    for agent in agents:
        assert get_agent_brain(agent.agent_key) is not None, agent.agent_key
        assert get_agent_capability(agent.agent_key) is not None, agent.agent_key


def test_every_runnable_registry_agent_is_fully_wired():
    for agent in list_registered_agents():
        if agent.run_action is None:
            continue
        policy = get_action_policy(agent.run_action)
        assert policy is not None, agent.run_action
        assert agent.run_action in TASKS, agent.run_action
        assert TASKS[agent.run_action]["agent_key"] == agent.agent_key
        assert agent.agent_key in RUNNERS, agent.agent_key


def test_every_master_ai_task_targets_registered_real_runner():
    registered = {agent.agent_key for agent in list_registered_agents()}
    for action, task in TASKS.items():
        assert get_action_policy(action) is not None, action
        assert task["agent_key"] in registered, task
        assert task["agent_key"] in RUNNERS, task


def test_capability_mode_matches_action_approval_for_runnable_agents():
    for agent in list_registered_agents():
        if not agent.run_action:
            continue
        policy = get_action_policy(agent.run_action)
        capability = get_agent_capability(agent.agent_key)
        assert policy is not None
        assert capability is not None
        if policy.approval == ApprovalLevel.AUTOMATIC:
            assert capability.mode in {CapabilityMode.RUN, CapabilityMode.READ}
            assert capability.owner_approval_required is False
        elif policy.approval == ApprovalLevel.OWNER_APPROVAL:
            assert capability.mode == CapabilityMode.APPROVAL
            assert capability.owner_approval_required is True


def test_embedded_and_diagnostic_agents_are_not_fake_worker_runners():
    expected_non_worker = {
        "master_ai",
        "macro_ai_agent",
        "economic_calendar_ai_agent",
        "website_health_agent",
        "delivery_monitor_agent",
        "scheduler_agent",
        "admin_support_agent",
        "report_agent",
    }
    by_key = {agent.agent_key: agent for agent in list_registered_agents()}
    for key in expected_non_worker:
        assert by_key[key].run_action is None


def test_native_allowlist_contains_only_safe_automatic_agents():
    expected = {
        "market_data_agent",
        "customer_support_agent",
        "marketing_strategy_agent",
        "social_media_agent",
        "cms_editor_agent",
        "master_content_review_agent",
    }
    assert set(ORCHESTRATION_NATIVE_AGENT_KEYS) == expected
    by_key = {agent.agent_key: agent for agent in list_registered_agents()}
    for key in expected:
        action = by_key[key].run_action
        assert action is not None
        assert get_action_policy(action).approval == ApprovalLevel.AUTOMATIC


def test_safe_registered_agent_intents_resolve_without_cross_agent_collision():
    cases = {
        "Run Market Data Agent": ("run_market_data_agent", "market_data_agent"),
        "Customer Support Agent se guidance banao": ("run_customer_support_agent", "customer_support_agent"),
        "Marketing Strategy Agent se marketing plan banao": ("run_marketing_strategy_agent", "marketing_strategy_agent"),
        "Social Media Agent se drafts banao": ("run_social_media_agent", "social_media_agent"),
        "CMS Editor Agent se draft banao": ("run_cms_editor_agent", "cms_editor_agent"),
        "Content Review Agent se review karo": ("run_master_ai_content_review_agent", "master_content_review_agent"),
    }
    for message, expected in cases.items():
        proposal = resolve_master_ai_intent(message)
        assert proposal.status == "RESOLVED", (message, proposal)
        assert (proposal.action, proposal.agent_key) == expected


def test_consequential_agent_intents_always_require_approval():
    cases = {
        "Signal Agent chalao": "run_signal_agent",
        "Telegram Reply Agent chalao": "run_telegram_reply_agent",
        "WhatsApp Reply Agent chalao": "run_whatsapp_reply_agent",
        "Announcement Agent chalao": "run_announcement_agent",
        "Publish Approval Agent chalao": "run_master_ai_publish_approval_agent",
        "SEO Agent chalao": "run_seo_agent",
    }
    for message, action in cases.items():
        proposal = resolve_master_ai_intent(message)
        assert proposal.status == "APPROVAL_REQUIRED", (message, proposal)
        assert proposal.action == action


def test_owner_approval_policy_blocks_runner_invocation():
    calls = []

    def runner(**kwargs):
        calls.append(kwargs)
        raise AssertionError("owner-gated runner must not be called")

    for action in (
        "run_signal_agent",
        "run_telegram_reply_agent",
        "run_whatsapp_reply_agent",
        "run_announcement_agent",
        "run_master_ai_publish_approval_agent",
        "run_seo_agent",
    ):
        result = execute_master_ai_action(action, runner=runner)
        assert result.ok is False
        assert result.status == "OWNER_APPROVAL_REQUIRED"
    assert calls == []


def test_planner_allows_native_agent_only_when_no_db_descriptor_exists():
    planner = ExecutionPlanner()
    task = SimpleNamespace(
        task_type="CUSTOMER_SUPPORT",
        title="Prepare support guidance",
        input_payload={"agent_keys": ["customer_support_agent"]},
    )
    plan = planner.build_plan(task=task, available_agents=[], context={})
    assert [step.agent_key for step in plan.steps] == ["customer_support_agent"]

    disabled = [
        AgentDescriptor(
            agent_key="customer_support_agent",
            display_name="Customer Support Agent",
            is_enabled=False,
        )
    ]
    with pytest.raises(ValueError, match="unavailable or disabled"):
        planner.build_plan(task=task, available_agents=disabled, context={})


def test_worker_adapter_uses_native_runner_only_for_master_ai(monkeypatch):
    calls = []
    monkeypatch.setitem(
        RUNNERS,
        "customer_support_agent",
        lambda payload: calls.append(dict(payload)) or "support draft ready",
    )
    adapter = WorkerAgentAdapter()
    result = adapter.execute_step(
        agent_key="customer_support_agent",
        trigger_type="MASTER_AI",
        triggered_by=None,
        payload={"customer_message": "How does onboarding work?"},
    )
    assert result.succeeded is True
    assert result.message == "support draft ready"
    assert calls == [{"customer_message": "How does onboarding work?"}]


def test_scheduled_or_consequential_agent_never_uses_native_allowlist():
    assert "signal_agent" not in ORCHESTRATION_NATIVE_AGENT_KEYS
    assert "telegram_reply_agent" not in ORCHESTRATION_NATIVE_AGENT_KEYS
    assert "whatsapp_reply_agent" not in ORCHESTRATION_NATIVE_AGENT_KEYS
    assert "announcement_agent" not in ORCHESTRATION_NATIVE_AGENT_KEYS
    assert "seo_agent" not in ORCHESTRATION_NATIVE_AGENT_KEYS
    assert "master_publish_approval_agent" not in ORCHESTRATION_NATIVE_AGENT_KEYS
