from datetime import date
from decimal import Decimal

from services.ai_agents.economic_calendar.models import NewsLockDecision
from services.captain_ai_engine import (
    CaptainDecision,
    CaptainDirection,
    assess_captain,
    build_five_day_context,
)
from services.master_ai_signal_reader import MasterAISignalSnapshot


def snap(
    day: int,
    *,
    high: str,
    low: str,
    cmp: str = "4400",
    buy_base: str = "4370",
    sell_base: str = "4430",
    buy_targets: tuple[str, ...] = (
        "4390", "4410", "4450", "4470", "4490", "4510",
    ),
    sell_targets: tuple[str, ...] = (
        "4410", "4390", "4370", "4350", "4330", "4310",
    ),
) -> MasterAISignalSnapshot:
    return MasterAISignalSnapshot(
        signal_date=date(2026, 8, day),
        open_price=Decimal(low),
        high_price=Decimal(high),
        low_price=Decimal(low),
        close_price=Decimal(cmp),
        day_high=Decimal(high),
        day_low=Decimal(low),
        step=None,
        range_value=None,
        buy_base=Decimal(buy_base),
        sell_base=Decimal(sell_base),
        mode="Aggressive (0.25)",
        latest_slot="02:30 PM TO 03:30 PM",
        live_cmp=Decimal(cmp),
        buy_targets=tuple(Decimal(x) for x in buy_targets),
        sell_targets=tuple(Decimal(x) for x in sell_targets),
    )


def bullish_history():
    return (
        snap(7, high="4400", low="4300"),
        snap(8, high="4420", low="4310"),
        snap(11, high="4440", low="4320"),
        snap(12, high="4460", low="4330"),
        snap(13, high="4480", low="4340"),
    )


def bearish_history():
    return (
        snap(7, high="4480", low="4380"),
        snap(8, high="4460", low="4360"),
        snap(11, high="4440", low="4340"),
        snap(12, high="4420", low="4320"),
        snap(13, high="4400", low="4300"),
    )


def test_builds_five_day_bullish_structure():
    ctx = build_five_day_context(bullish_history())
    assert ctx is not None
    assert ctx.trading_days == 5
    assert ctx.weekly_high == Decimal("4480")
    assert ctx.weekly_low == Decimal("4300")
    assert ctx.bias == "BULLISH"


def test_mid_range_entry_is_blocked():
    current = snap(
        14,
        high="4450",
        low="4350",
        cmp="4400",
        buy_base="4370",
        sell_base="4430",
    )

    result = assess_captain(
        current=current,
        history=bullish_history(),
    )

    assert result.decision is CaptainDecision.WAIT
    assert result.direction is CaptainDirection.NONE
    assert "mid-range" in result.reasons[0]


def test_high_impact_news_forces_wait():
    current = snap(
        14,
        high="4450",
        low="4350",
        cmp="4368",
    )

    lock = NewsLockDecision(
        locked=True,
        reason="High-impact USD event nearby.",
        event_id="us-cpi",
        seconds_to_event=900,
    )

    result = assess_captain(
        current=current,
        history=bullish_history(),
        news_lock=lock,
    )

    assert result.decision is CaptainDecision.WAIT
    assert result.news_locked is True


def test_buy_can_be_approved_near_buy_base_with_six_targets():
    current = snap(
        14,
        high="4490",
        low="4360",
        cmp="4368",
        buy_base="4370",
        sell_base="4450",
        buy_targets=(
            "4390", "4410", "4430", "4450", "4470", "4490",
        ),
    )

    result = assess_captain(
        current=current,
        history=bullish_history(),
    )

    assert result.decision is CaptainDecision.APPROVE
    assert result.direction is CaptainDirection.BUY
    assert len(result.targets) == 6


def test_sell_can_be_approved_near_sell_base_with_six_targets():
    current = snap(
        14,
        high="4440",
        low="4280",
        cmp="4432",
        buy_base="4310",
        sell_base="4430",
        sell_targets=(
            "4410", "4390", "4370", "4350", "4330", "4310",
        ),
    )

    result = assess_captain(
        current=current,
        history=bearish_history(),
    )

    assert result.decision is CaptainDecision.APPROVE
    assert result.direction is CaptainDirection.SELL


def test_missing_official_six_targets_is_rejected():
    current = snap(
        14,
        high="4490",
        low="4360",
        cmp="4368",
        buy_targets=("4390", "4410"),
    )

    result = assess_captain(
        current=current,
        history=bullish_history(),
    )

    assert result.decision is CaptainDecision.REJECT


def test_countertrend_buy_waits():
    current = snap(
        14,
        high="4410",
        low="4280",
        cmp="4368",
        buy_base="4370",
        buy_targets=(
            "4390", "4410", "4430", "4450", "4470", "4490",
        ),
    )

    result = assess_captain(
        current=current,
        history=bearish_history(),
    )

    assert result.decision is CaptainDecision.WAIT
    assert result.direction is CaptainDirection.BUY


def test_buy_uses_active_session_low_as_stop_loss():
    current = snap(
        14,
        high="4401.02",
        low="4351.80",
        cmp="4355.78",
        buy_base="4359.77",
        sell_base="4390.99",
        buy_targets=(
            "4372.08", "4384.39", "4396.70",
            "4409.01", "4421.32", "4433.63",
        ),
    )

    result = assess_captain(
        current=current,
        history=bullish_history(),
    )

    assert result.decision is CaptainDecision.APPROVE
    assert result.direction is CaptainDirection.BUY
    assert result.stop_loss == Decimal("4351.80")


def test_sell_uses_active_session_high_as_stop_loss():
    current = snap(
        14,
        high="4449.78",
        low="4364.91",
        cmp="4436.24",
        buy_base="4372.27",
        sell_base="4430.93",
        sell_targets=(
            "4409.71", "4388.49", "4367.27",
            "4346.05", "4324.83", "4303.61",
        ),
    )

    result = assess_captain(
        current=current,
        history=bearish_history(),
    )

    assert result.decision is CaptainDecision.APPROVE
    assert result.direction is CaptainDirection.SELL
    assert result.stop_loss == Decimal("4449.78")


def test_invalid_same_session_stop_loss_rejects():
    current = snap(
        14,
        high="4490",
        low="4370",
        cmp="4368",
        buy_base="4370",
        sell_base="4450",
        buy_targets=(
            "4390", "4410", "4430",
            "4450", "4470", "4490",
        ),
    )

    result = assess_captain(
        current=current,
        history=bullish_history(),
    )

    assert result.decision is CaptainDecision.REJECT


def test_matching_bullish_macro_boosts_buy_confidence():
    current = snap(
        14,
        high="4401.02",
        low="4351.80",
        cmp="4355.78",
        buy_base="4359.77",
        sell_base="4390.99",
        buy_targets=(
            "4372.08", "4384.39", "4396.70",
            "4409.01", "4421.32", "4433.63",
        ),
    )

    result = assess_captain(
        current=current,
        history=bullish_history(),
        macro_bias="BULLISH_GOLD",
        macro_confidence=95,
    )

    assert result.decision is CaptainDecision.APPROVE
    assert result.direction is CaptainDirection.BUY
    assert result.macro_bias == "BULLISH_GOLD"
    assert result.macro_confidence == 95
    assert result.confidence > 85
    assert "Macro-news bias supports BUY." in result.reasons


def test_conflicting_bearish_macro_reduces_buy_confidence():
    current = snap(
        14,
        high="4401.02",
        low="4351.80",
        cmp="4355.78",
        buy_base="4359.77",
        sell_base="4390.99",
        buy_targets=(
            "4372.08", "4384.39", "4396.70",
            "4409.01", "4421.32", "4433.63",
        ),
    )

    result = assess_captain(
        current=current,
        history=bullish_history(),
        macro_bias="BEARISH_GOLD",
        macro_confidence=95,
    )

    assert result.decision is CaptainDecision.APPROVE
    assert result.direction is CaptainDirection.BUY
    assert result.macro_bias == "BEARISH_GOLD"
    assert result.confidence < 85
    assert (
        "Macro-news bias conflicts with technical direction."
        in result.reasons
    )


def test_buy_waits_when_target1_reward_risk_is_below_one():
    current = snap(
        14,
        high="4354.26",
        low="4347.26",
        cmp="4350.76",
        buy_base="4350.76",
        sell_base="4365.00",
        buy_targets=(
            "4352.51",
            "4354.26",
            "4356.01",
            "4357.76",
            "4359.51",
            "4361.26",
        ),
    )

    result = assess_captain(
        current=current,
        history=bullish_history(),
    )

    assert result.decision is CaptainDecision.WAIT
    assert result.direction is CaptainDirection.BUY
    assert result.stop_loss == Decimal("4347.26")
    assert any(
        "reward/risk is too weak" in reason
        for reason in result.reasons
    )
