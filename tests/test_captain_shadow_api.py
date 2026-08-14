from decimal import Decimal
from types import SimpleNamespace

from fastapi.testclient import TestClient

import backend
from services import captain_shadow_api


def _assessment():
    return SimpleNamespace(
        decision=SimpleNamespace(value="WAIT"),
        direction=SimpleNamespace(value="BUY"),
        confidence=90,
        weekly=SimpleNamespace(
            trading_days=5,
            weekly_high=Decimal("4449.78"),
            weekly_low=Decimal("4313.51"),
            weekly_range=Decimal("136.27"),
            average_daily_range=Decimal("62.442"),
            higher_highs=2,
            lower_highs=1,
            higher_lows=2,
            lower_lows=1,
            bias="BULLISH",
        ),
        live_cmp=Decimal("4350.76"),
        buy_base=Decimal("4350.76"),
        sell_base=Decimal("4365.00"),
        targets=(
            Decimal("4352.51"),
            Decimal("4354.26"),
        ),
        stop_loss=Decimal("4347.26"),
        news_locked=False,
        macro_bias="BULLISH_GOLD",
        macro_confidence=95,
        reasons=(
            "BUY Target 1 reward/risk is too weak: "
            "0.50R; minimum is 1.00R.",
        ),
        read_only=True,
        signal_generated=False,
        delivery_started=False,
    )


def test_shadow_endpoint_is_not_available_when_disabled(
    monkeypatch,
):
    monkeypatch.delenv(
        "CAPTAIN_SIGNAL_SHADOW_GATE",
        raising=False,
    )

    client = TestClient(backend.app)
    response = client.get(
        "/internal/captain/shadow",
    )

    assert response.status_code == 404


def test_shadow_endpoint_returns_read_only_assessment(
    monkeypatch,
):
    monkeypatch.setenv(
        "CAPTAIN_SIGNAL_SHADOW_GATE",
        "1",
    )

    monkeypatch.setattr(
        captain_shadow_api,
        "_require_bff",
        lambda value: None,
    )
    monkeypatch.setattr(
        captain_shadow_api,
        "run_captain_read_only",
        _assessment,
    )

    client = TestClient(backend.app)
    response = client.get(
        "/internal/captain/shadow",
        headers={
            "X-Admin-BFF-Key": "test-only",
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["mode"] == "CAPTAIN_SHADOW"
    assert payload["decision"] == "WAIT"
    assert payload["direction"] == "BUY"
    assert payload["confidence"] == 90
    assert payload["read_only"] is True
    assert payload["signal_generated"] is False
    assert payload["delivery_started"] is False
    assert payload["live_cmp"] == "4350.76"
    assert payload["stop_loss"] == "4347.26"
    assert "reward/risk is too weak" in payload["reasons"][0]
    assert response.headers["cache-control"] == (
        "private, no-store"
    )


def test_shadow_endpoint_runtime_failure_is_safe(
    monkeypatch,
):
    monkeypatch.setenv(
        "CAPTAIN_SIGNAL_SHADOW_GATE",
        "1",
    )

    monkeypatch.setattr(
        captain_shadow_api,
        "_require_bff",
        lambda value: None,
    )

    def fail():
        raise RuntimeError(
            "token=secret /private/path traceback"
        )

    monkeypatch.setattr(
        captain_shadow_api,
        "run_captain_read_only",
        fail,
    )

    client = TestClient(backend.app)
    response = client.get(
        "/internal/captain/shadow",
        headers={
            "X-Admin-BFF-Key": "test-only",
        },
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Captain shadow assessment unavailable."
    }

    body = response.text.lower()
    assert "token=secret" not in body
    assert "private/path" not in body
    assert "traceback" not in body
