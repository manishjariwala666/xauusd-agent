from services.master_ai_capability_matrix import (
    AgentRiskLevel,
    CapabilityMode,
    get_agent_capability,
    list_agent_capabilities,
)
from services.master_ai_agent_registry import list_registered_agents


def test_all_registered_agents_have_capability_policy() -> None:
    registered = {
        agent.agent_key
        for agent in list_registered_agents()
    }
    configured = {
        capability.agent_key
        for capability in list_agent_capabilities()
    }

    assert registered == configured


def test_external_reply_agents_are_blocked() -> None:
    for key in (
        "telegram_reply_agent",
        "whatsapp_reply_agent",
        "customer_support_agent",
    ):
        capability = get_agent_capability(key)

        assert capability is not None
        assert capability.mode is CapabilityMode.BLOCKED
        assert capability.owner_approval_required is True


def test_macro_and_calendar_agents_are_read_only() -> None:
    for key in (
        "macro_ai_agent",
        "economic_calendar_ai_agent",
    ):
        capability = get_agent_capability(key)

        assert capability is not None
        assert capability.mode is CapabilityMode.READ
        assert capability.risk is AgentRiskLevel.READ_ONLY


def test_only_selected_agents_are_directly_runnable() -> None:
    runnable = {
        capability.agent_key
        for capability in list_agent_capabilities()
        if capability.mode is CapabilityMode.RUN
    }

    assert runnable == {
        "signal_agent",
        "market_data_agent",
    }
