"""Contract tests for VenusRealm agent brain policies."""

from services.agent_brain_contracts import (
    AGENT_BRAINS,
    AgentBrainContract,
    AgentRisk,
    get_agent_brain,
    list_agent_brains,
)
from services.master_ai_agent_registry import list_registered_agents


def test_every_registered_agent_has_exactly_one_brain_contract() -> None:
    registered_keys = {agent.agent_key for agent in list_registered_agents()}
    brain_keys = set(AGENT_BRAINS)

    assert brain_keys == registered_keys


def test_brain_contract_keys_match_mapping_keys() -> None:
    for mapping_key, contract in AGENT_BRAINS.items():
        assert isinstance(contract, AgentBrainContract)
        assert contract.agent_key == mapping_key


def test_all_brain_contracts_have_required_policy_fields() -> None:
    for contract in list_agent_brains():
        assert contract.agent_key
        assert contract.display_name
        assert contract.purpose
        assert contract.allowed_inputs
        assert contract.allowed_tools
        assert contract.output_schema
        assert contract.idempotency_strategy
        assert contract.retry_policy
        assert contract.human_takeover_policy
        assert contract.audit_policy
        assert contract.safe_error_policy
        assert isinstance(contract.default_risk, AgentRisk)


def test_master_ai_forbidden_actions_are_locked() -> None:
    contract = get_agent_brain("master_ai")

    assert contract is not None
    assert "execute_trade" in contract.forbidden_actions
    assert "expose_secrets" in contract.forbidden_actions
    assert "delete_production_data" in contract.forbidden_actions
    assert "bypass_approval" in contract.forbidden_actions


def test_signal_agent_never_executes_trades_or_invents_values() -> None:
    contract = get_agent_brain("signal_agent")

    assert contract is not None
    assert "execute_trade" in contract.forbidden_actions
    assert "invent_price" in contract.forbidden_actions
    assert "invent_target" in contract.forbidden_actions
    assert "invent_result" in contract.forbidden_actions


def test_external_delivery_agents_require_approval_for_sensitive_actions() -> None:
    whatsapp = get_agent_brain("whatsapp_reply_agent")
    telegram = get_agent_brain("telegram_reply_agent")
    announcement = get_agent_brain("announcement_agent")

    assert whatsapp is not None
    assert telegram is not None
    assert announcement is not None

    assert "first_outbound_contact" in whatsapp.approval_required_actions
    assert "broadcast_message" in telegram.approval_required_actions
    assert "immediate_broadcast" in announcement.approval_required_actions


def test_read_only_agents_default_to_read_only_risk() -> None:
    read_only_agents = (
        "website_health_agent",
        "delivery_monitor_agent",
        "scheduler_agent",
        "admin_support_agent",
        "report_agent",
    )

    for agent_key in read_only_agents:
        contract = get_agent_brain(agent_key)

        assert contract is not None
        assert contract.default_risk == AgentRisk.READ_ONLY


def test_unknown_agent_has_no_brain_contract() -> None:
    assert get_agent_brain("unknown_agent") is None


from services.master_ai_agent_registry import (
    get_agent_dashboard_record,
    list_agent_dashboard_records,
)


def test_dashboard_records_cover_all_registered_agents() -> None:
    records = list_agent_dashboard_records()

    assert len(records) == len(list_registered_agents())
    assert {record["agent_key"] for record in records} == set(AGENT_BRAINS)


def test_dashboard_record_exposes_safe_brain_metadata() -> None:
    signal_agent = next(
        agent
        for agent in list_registered_agents()
        if agent.agent_key == "signal_agent"
    )

    record = get_agent_dashboard_record(signal_agent)

    assert record["agent_key"] == "signal_agent"
    assert record["brain_configured"] is True
    assert record["default_risk"] == "HIGH"
    assert "manual_signal_run" in record["approval_required_actions"]
    assert "execute_trade" in record["forbidden_actions"]
    assert "signal_id" in record["output_schema"]


def test_dashboard_records_do_not_expose_sensitive_configuration() -> None:
    forbidden_fields = {
        "token",
        "secret",
        "password",
        "credential",
        "database_url",
        "api_key",
    }

    for record in list_agent_dashboard_records():
        assert forbidden_fields.isdisjoint(record)
