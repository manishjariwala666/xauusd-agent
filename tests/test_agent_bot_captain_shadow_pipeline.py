from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import agent_bot


class FakeSheets:
    def get_latest_signal(self):
        return SimpleNamespace(
            external_key="shadow-e2e-1",
            reference_price=Decimal("4342.54"),
            observed_at=datetime(
                2026, 8, 14, 8, 30,
                tzinfo=timezone.utc,
            ),
            source="GOOGLE_SHEET",
            direction="BUY",
            target_price=Decimal("4372.08"),
            stop_loss=Decimal("4317.63"),
            label="EVENING SESSION",
            targets=(
                Decimal("4372.08"),
                Decimal("4384.39"),
                Decimal("4396.70"),
            ),
            target_slots=(),
        )


class FakeMarketData:
    def __init__(self):
        self.insert_calls = 0

    def signal_exists(self, external_key):
        assert external_key == "shadow-e2e-1"
        return False

    def insert_signal(self, **kwargs):
        self.insert_calls += 1
        return {
            "id": "shadow-e2e-signal",
            "signal_type": kwargs["signal_type"],
            "price": float(kwargs["market_price"].price),
            "target_1": 4372.08,
            "target_2": 4384.39,
            "target_3": 4396.70,
            "stop_loss": 4317.63,
        }


class FakeTelegram:
    def __init__(self):
        self.send_signal_calls = 0
        self.broadcast_calls = 0

    def send_signal(self, signal, test=False):
        self.send_signal_calls += 1
        return False

    def broadcast_pending_signals(self):
        self.broadcast_calls += 1
        raise AssertionError(
            "broadcast_pending_signals must not run in shadow mode"
        )


def test_shadow_pipeline_inserts_candidate_and_blocks_outbound(
    monkeypatch,
):
    monkeypatch.setenv(
        "CAPTAIN_SIGNAL_SHADOW_GATE",
        "1",
    )

    whatsapp_calls = {"count": 0}

    def fake_whatsapp():
        whatsapp_calls["count"] += 1
        raise AssertionError(
            "WhatsApp delivery must not run in shadow mode"
        )

    monkeypatch.setattr(
        agent_bot,
        "deliver_pending_whatsapp_signals",
        fake_whatsapp,
    )

    monkeypatch.setattr(
        "services.captain_ai_runtime.run_captain_read_only",
        lambda: _captain_result("APPROVE", "BUY"),
    )

    sheets = FakeSheets()
    market = FakeMarketData()
    telegram = FakeTelegram()

    agent_bot.run_pipeline_once(
        sheets,
        market,
        telegram,
    )

    assert market.insert_calls == 1
    assert telegram.send_signal_calls == 1
    assert telegram.broadcast_calls == 0
    assert whatsapp_calls["count"] == 0


def _captain_result(
    decision,
    direction,
    reasons=("test",),
):
    from types import SimpleNamespace

    return SimpleNamespace(
        decision=SimpleNamespace(value=decision),
        direction=SimpleNamespace(value=direction),
        reasons=reasons,
    )


def test_wait_never_inserts_or_delivers(monkeypatch):
    monkeypatch.delenv(
        "CAPTAIN_SIGNAL_SHADOW_GATE",
        raising=False,
    )

    monkeypatch.setattr(
        "services.captain_ai_runtime.run_captain_read_only",
        lambda: _captain_result("WAIT", "BUY"),
    )

    market = FakeMarketData()
    telegram = FakeTelegram()

    whatsapp = {"count": 0}

    monkeypatch.setattr(
        agent_bot,
        "deliver_pending_whatsapp_signals",
        lambda: whatsapp.__setitem__(
            "count",
            whatsapp["count"] + 1,
        ),
    )

    agent_bot.run_pipeline_once(
        FakeSheets(),
        market,
        telegram,
    )

    assert market.insert_calls == 0
    assert telegram.send_signal_calls == 0
    assert telegram.broadcast_calls == 0
    assert whatsapp["count"] == 0


def test_direction_mismatch_never_inserts_or_delivers(
    monkeypatch,
):
    monkeypatch.delenv(
        "CAPTAIN_SIGNAL_SHADOW_GATE",
        raising=False,
    )

    monkeypatch.setattr(
        "services.captain_ai_runtime.run_captain_read_only",
        lambda: _captain_result("APPROVE", "SELL"),
    )

    market = FakeMarketData()
    telegram = FakeTelegram()

    agent_bot.run_pipeline_once(
        FakeSheets(),
        market,
        telegram,
    )

    assert market.insert_calls == 0
    assert telegram.broadcast_calls == 0


def test_captain_failure_fails_closed(monkeypatch):
    monkeypatch.delenv(
        "CAPTAIN_SIGNAL_SHADOW_GATE",
        raising=False,
    )

    def fail():
        raise RuntimeError("captain unavailable")

    monkeypatch.setattr(
        "services.captain_ai_runtime.run_captain_read_only",
        fail,
    )

    market = FakeMarketData()
    telegram = FakeTelegram()

    agent_bot.run_pipeline_once(
        FakeSheets(),
        market,
        telegram,
    )

    assert market.insert_calls == 0
    assert telegram.broadcast_calls == 0
