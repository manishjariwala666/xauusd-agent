from types import SimpleNamespace

from services.telegram_primary_delivery import deliver_pending_telegram_signals


class FakeBot:
    def __init__(self):
        self.calls = []

    def send_message(self, recipient, message, disable_web_page_preview=False):
        self.calls.append((recipient, message, disable_web_page_preview))
        return SimpleNamespace(message_id=321)


class FakeTelegram:
    def __init__(self):
        self._chat_id = "-100123"
        self._bot = FakeBot()

    @staticmethod
    def format_message(signal):
        return f"{signal['signal_type']} {signal['id']}"


def test_missing_transport_fails_closed(monkeypatch):
    telegram = FakeTelegram()
    telegram._chat_id = ""

    called = False

    def durable(**kwargs):
        nonlocal called
        called = True
        return 1, 0

    monkeypatch.setattr(
        "services.telegram_primary_delivery.deliver_pending_signal_recipients",
        durable,
    )

    assert deliver_pending_telegram_signals(telegram) == (0, 0)
    assert called is False


def test_telegram_uses_shared_durable_contract(monkeypatch):
    telegram = FakeTelegram()
    captured = {}

    monkeypatch.setattr(
        "services.telegram_primary_delivery.evaluate_signal_shadow_gate",
        lambda signal: SimpleNamespace(blocked=False, reason="verified"),
    )

    def durable(**kwargs):
        captured.update(kwargs)
        assert kwargs["channel"] == "telegram"
        assert kwargs["recipients"] == ("-100123",)
        assert kwargs["max_attempts"] == 3
        assert kwargs["format_message"]({"signal_type": "BUY", "id": 7}) == "BUY 7"
        allowed, reason = kwargs["verify_signal"]({"signal_type": "BUY", "id": 7})
        assert allowed is True
        assert reason == "verified"
        assert kwargs["send"]("-100123", "BUY 7") == "321"
        return 1, 0

    monkeypatch.setattr(
        "services.telegram_primary_delivery.deliver_pending_signal_recipients",
        durable,
    )

    assert deliver_pending_telegram_signals(telegram) == (1, 0)
    assert telegram._bot.calls == [("-100123", "BUY 7", True)]
    assert captured["channel"] == "telegram"


def test_captain_block_is_forwarded_to_durable_verifier(monkeypatch):
    telegram = FakeTelegram()

    monkeypatch.setattr(
        "services.telegram_primary_delivery.evaluate_signal_shadow_gate",
        lambda signal: SimpleNamespace(blocked=True, reason="Captain WAIT"),
    )

    def durable(**kwargs):
        allowed, reason = kwargs["verify_signal"]({"signal_type": "SELL", "id": 9})
        assert allowed is False
        assert reason == "Captain WAIT"
        return 0, 0

    monkeypatch.setattr(
        "services.telegram_primary_delivery.deliver_pending_signal_recipients",
        durable,
    )

    assert deliver_pending_telegram_signals(telegram) == (0, 0)
    assert telegram._bot.calls == []
