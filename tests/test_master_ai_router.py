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
    monkeypatch.setattr(
        "services.master_ai_signal_reader.get_signal_snapshot_for_date",
        lambda _: None,
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


def test_market_data_reply_uses_stale_reference_when_today_is_blank(
    monkeypatch,
) -> None:
    from datetime import date
    from decimal import Decimal

    from services.master_ai_signal_reader import MasterAISignalSnapshot
    from services.master_ai_chat_service import generate_master_ai_reply

    monkeypatch.setattr(
        "services.master_ai_chat_service.get_today_signal_snapshot",
        lambda: None,
    )

    stale = MasterAISignalSnapshot(
        signal_date=date(2026, 8, 6),
        open_price=None,
        high_price=None,
        low_price=None,
        close_price=None,
        day_high=None,
        day_low=None,
        step=None,
        range_value=None,
        buy_base=None,
        sell_base=None,
        mode="",
        latest_slot="10:30 PM TO 11:30 PM",
        live_cmp=Decimal("4246.65"),
        buy_targets=(),
        sell_targets=(),
    )

    monkeypatch.setattr(
        "services.master_ai_signal_reader.get_signal_snapshot_for_date",
        lambda _: stale,
    )

    result = generate_master_ai_reply("XAUUSD current price kya hai?")

    assert "4246.65" in result
    assert "STALE REFERENCE" in result
    assert "not current live price" in result


def test_routes_gold_outlook_to_unified_intelligence() -> None:
    route = route_master_ai_request("Gold ka outlook kya hai?")

    assert route.intent == "MARKET_OUTLOOK"
    assert route.agent_key == "master_ai"
    assert route.execution_allowed is False


def test_routes_macro_bias_to_macro_ai() -> None:
    route = route_master_ai_request("Macro bias for gold?")

    assert route.intent == "MACRO_OUTLOOK"
    assert route.agent_key == "macro_ai_agent"
    assert route.execution_allowed is False


def test_routes_high_impact_news_to_calendar_ai() -> None:
    route = route_master_ai_request("Aaj high impact news risk kya hai?")

    assert route.intent == "NEWS_RISK"
    assert route.agent_key == "economic_calendar_ai_agent"
    assert route.execution_allowed is False


def test_routes_safe_to_trade_to_wait_assessment() -> None:
    route = route_master_ai_request("Abhi trade karna safe hai?")

    assert route.intent == "WAIT_OR_TRADE"
    assert route.agent_key == "master_ai"
    assert route.execution_allowed is False


def test_market_outlook_returns_read_only_incomplete_assessment(
    monkeypatch,
) -> None:
    from services.master_ai_chat_service import generate_master_ai_reply

    monkeypatch.setattr(
        "services.master_ai_chat_service.get_today_signal_snapshot",
        lambda: None,
    )
    monkeypatch.setattr(
        "services.master_ai_chat_service.load_macro_assessment",
        lambda: None,
    )

    reply = generate_master_ai_reply("Gold ka outlook kya hai?")

    assert "Read-only assessment only." in reply
    assert "Decision: INCOMPLETE" in reply
    assert "No signal" in reply


def test_macro_outlook_never_guesses_missing_provider(
    monkeypatch,
) -> None:
    from services.master_ai_chat_service import generate_master_ai_reply

    monkeypatch.setattr(
        "services.master_ai_chat_service.get_today_signal_snapshot",
        lambda: None,
    )
    monkeypatch.setattr(
        "services.master_ai_chat_service.load_macro_assessment",
        lambda: None,
    )

    reply = generate_master_ai_reply("Macro bias for gold?")

    assert "Macro provider is temporarily unavailable" in reply
    assert "no macro bias was guessed" in reply

def test_news_risk_never_invents_calendar_event(
    monkeypatch,
) -> None:
    from services.master_ai_chat_service import generate_master_ai_reply

    monkeypatch.setattr(
        "services.master_ai_chat_service.get_today_signal_snapshot",
        lambda: None,
    )

    reply = generate_master_ai_reply("Aaj high impact news risk kya hai?")

    assert "Economic calendar provider is not connected yet" in reply
    assert "no news event was invented" in reply


def test_macro_outlook_uses_read_only_macro_provider(
    monkeypatch,
) -> None:
    from datetime import datetime, timezone
    from decimal import Decimal

    from services.ai_agents.macro_ai.models import (
        GoldBias,
        MacroAssessment,
    )
    from services.master_ai_chat_service import generate_master_ai_reply

    monkeypatch.setattr(
        "services.master_ai_chat_service.get_today_signal_snapshot",
        lambda: None,
    )
    monkeypatch.setattr(
        "services.master_ai_chat_service.load_macro_assessment",
        lambda: MacroAssessment(
            bias=GoldBias.BUY,
            confidence=81,
            total_score=Decimal("0.42"),
            observed_at=datetime.now(timezone.utc),
            drivers=(),
            conflicts=("US2Y data missing",),
            source_count=8,
        ),
    )

    reply = generate_master_ai_reply("Macro bias for gold?")

    assert "Decision: BULLISH" in reply
    assert "Macro: BUY (81%)" in reply
    assert "US2Y data missing" in reply
    assert "No signal" in reply


def test_macro_provider_failure_remains_no_guess(
    monkeypatch,
) -> None:
    from services.master_ai_chat_service import generate_master_ai_reply

    monkeypatch.setattr(
        "services.master_ai_chat_service.get_today_signal_snapshot",
        lambda: None,
    )
    monkeypatch.setattr(
        "services.master_ai_chat_service.load_macro_assessment",
        lambda: None,
    )

    reply = generate_master_ai_reply("Macro bias for gold?")

    assert "temporarily unavailable" in reply
    assert "no macro bias was guessed" in reply
