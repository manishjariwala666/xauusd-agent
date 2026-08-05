"""Tests for Master AI deterministic routing."""

from services.master_ai_router import route_master_ai_request


def test_routes_xauusd_current_price_to_market_data_agent() -> None:
    route = route_master_ai_request(
        "Current XAUUSD price?"
    )

    assert route.intent == "MARKET_DATA"
    assert route.agent_key == "market_data_agent"
    assert route.execution_allowed is True
    assert route.confidence == "HIGH"


def test_routes_hinglish_gold_price_to_market_data_agent() -> None:
    route = route_master_ai_request(
        "abhi gold price kya chal raha hai"
    )

    assert route.intent == "MARKET_DATA"
    assert route.agent_key == "market_data_agent"


def test_routes_customer_support_request() -> None:
    route = route_master_ai_request(
        "Customer ka subscription refund issue hai"
    )

    assert route.intent == "CUSTOMER_SUPPORT"
    assert route.agent_key == "customer_support_agent"
    assert route.execution_allowed is False


def test_publish_is_approval_locked() -> None:
    route = route_master_ai_request(
        "Publish draft now"
    )

    assert route.intent == "PUBLISH"
    assert route.agent_key == "master_publish_approval_agent"
    assert route.execution_allowed is False


def test_unknown_message_uses_general_chat() -> None:
    route = route_master_ai_request(
        "Explain VenusRealm architecture"
    )

    assert route.intent == "GENERAL_CHAT"
    assert route.agent_key is None


def test_empty_message_is_rejected() -> None:
    route = route_master_ai_request("")

    assert route.intent == "EMPTY"
    assert route.execution_allowed is False


def test_chat_service_returns_verified_sheet_price_without_llm(
    monkeypatch,
) -> None:
    from datetime import date
    from decimal import Decimal

    from services.master_ai_chat_service import (
        generate_master_ai_reply,
    )
    from services.master_ai_signal_reader import (
        MasterAISignalSnapshot,
    )

    snapshot = MasterAISignalSnapshot(
        signal_date=date(2026, 8, 5),
        open_price=Decimal("4156.96"),
        high_price=Decimal("4267.14"),
        low_price=Decimal("4150.28"),
        close_price=Decimal("4251.05"),
        day_high=Decimal("4267.14"),
        day_low=Decimal("4150.28"),
        step=Decimal("29.21"),
        range_value=Decimal("116.86"),
        buy_base=Decimal("4210.00"),
        sell_base=Decimal("4260.00"),
        mode="STANDARD",
        latest_slot="10:30 PM TO 11:30 PM",
        live_cmp=Decimal("4251.05"),
        buy_targets=(),
        sell_targets=(),
    )

    monkeypatch.setattr(
        "services.master_ai_chat_service.get_today_signal_snapshot",
        lambda: snapshot,
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    reply = generate_master_ai_reply(
        "XAUUSD ka current price?"
    )

    assert "Current Price: 4251.05" in reply
    assert "Day High: 4267.14" in reply
    assert "Day Low: 4150.28" in reply
    assert "Google Sheet Reference" in reply
    assert "Koi buy/sell signal" in reply


def test_chat_service_does_not_invent_missing_market_price(
    monkeypatch,
) -> None:
    from services.master_ai_chat_service import (
        generate_master_ai_reply,
    )

    monkeypatch.setattr(
        "services.master_ai_chat_service.get_today_signal_snapshot",
        lambda: None,
    )

    reply = generate_master_ai_reply(
        "Current gold price?"
    )

    assert "snapshot available nahi hai" in reply
    assert "guess nahi karunga" in reply


def test_chat_service_publish_request_remains_locked(
    monkeypatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    from services.master_ai_chat_service import (
        generate_master_ai_reply,
    )

    reply = generate_master_ai_reply(
        "Publish draft now"
    )

    assert "approval-locked" in reply
    assert "explicit owner approval" in reply
