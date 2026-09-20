from services.agent_brain_registry import get_agent_brain
from services.master_ai_agent_registry import list_registered_agents
from services.master_ai_capability_matrix import get_agent_capability


def test_registered_agents_have_standard_role_contracts() -> None:
    agents = list_registered_agents()
    assert agents

    for agent in agents:
        capability = get_agent_capability(agent.agent_key)
        brain = get_agent_brain(agent.agent_key)

        assert capability is not None, agent.agent_key
        assert brain is not None, agent.agent_key
        assert capability.agent_key == agent.agent_key
        assert brain.agent_key == agent.agent_key
        assert capability.allowed_actions or capability.blocked_actions
        assert brain.purpose
        assert brain.output_schema
        assert brain.audit_policy
        assert brain.safe_error_policy


def test_standard_roles_keep_high_impact_actions_gated() -> None:
    for agent in list_registered_agents():
        capability = get_agent_capability(agent.agent_key)
        if capability is None:
            continue

        if capability.owner_approval_required:
            assert capability.mode.value in {"READ", "APPROVAL", "BLOCKED"}
            assert capability.owner_approval_actions or capability.blocked_actions
