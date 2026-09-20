from services.master_ai_agent_registry import list_registered_agents
from services.master_ai_capability_matrix import get_agent_capability
from services.agent_brain_registry import get_agent_brain
from services.production_agents import RUNNERS
from services.worker_agent_adapter import ORCHESTRATION_NATIVE_AGENT_KEYS


def test_every_registered_agent_has_one_standard_role_contract():
    registered = list_registered_agents()
    assert registered

    for agent in registered:
        capability = get_agent_capability(agent.agent_key)
        brain = get_agent_brain(agent.agent_key)

        assert capability is not None, f"{agent.agent_key}: missing capability contract"
        assert brain is not None, f"{agent.agent_key}: missing brain/job-role contract"
        assert brain.agent_key == agent.agent_key
        assert capability.agent_key == agent.agent_key
        assert brain.purpose.strip(), f"{agent.agent_key}: empty job role purpose"
        assert capability.allowed_actions, f"{agent.agent_key}: no allowed actions"
        assert capability.blocked_actions, f"{agent.agent_key}: no blocked actions"


def test_executable_agents_have_an_explicit_execution_path():
    registered = {agent.agent_key for agent in list_registered_agents()}

    for agent_key in registered:
        capability = get_agent_capability(agent_key)
        if capability is None:
            continue

        if agent_key == "master_ai":
            continue

        if capability.mode.value in {"RUN", "APPROVAL"}:
            assert (
                agent_key in RUNNERS
                or agent_key in ORCHESTRATION_NATIVE_AGENT_KEYS
            ), f"{agent_key}: executable role has no production execution path"


def test_forbidden_actions_are_present_for_every_role():
    for agent in list_registered_agents():
        capability = get_agent_capability(agent.agent_key)
        brain = get_agent_brain(agent.agent_key)
        assert capability is not None
        assert brain is not None
        assert brain.forbidden_actions
        assert capability.blocked_actions
