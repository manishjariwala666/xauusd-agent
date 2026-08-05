"""Tests for Venus Market Data Agent."""

from datetime import datetime, timezone
import json

import pytest

from services.market_data_agent import (
    build_market_snapshot,
    run_market_data_agent,
)


NOW = datetime(
    2026,
    8,
    5,
    18,
    0,
    tzinfo=timezone.utc,
)


def _payload() -> dict:
    return {
        "symbol": "XAUUSD",
        "price": "3345.20",
        "source": "GOOGLE_FINANCE_SHEET",
        "updated_at": "2026-08-05T17:55:00+00:00",
        "max_age_seconds": 1200,
    }


def test_google_finance_is_reference_data() -> None:
    result = build_market_snapshot(
        _payload(),
        now=NOW,
    )

    assert result["status"] == "AVAILABLE"
    assert result["data_class"] == "REFERENCE_DATA"
    assert result["source_label"] == (
        "Google Finance reference price"
    )
    assert result["fresh"] is True
    assert result["signal_generated"] is False


def test_broker_feed_can_be_labelled_live() -> None:
    payload = _payload()
    payload.update({
        "source": "MT5",
        "bid": "3345.10",
        "ask": "3345.30",
    })

    result = build_market_snapshot(
        payload,
        now=NOW,
    )

    assert result["data_class"] == "LIVE_BROKER_DATA"
    assert result["source_label"] == "Live broker price"
    assert result["spread"] == "0.20"


def test_stale_price_is_blocked() -> None:
    payload = _payload()
    payload["updated_at"] = (
        "2026-08-05T16:00:00+00:00"
    )

    with pytest.raises(PermissionError):
        build_market_snapshot(
            payload,
            now=NOW,
        )


@pytest.mark.parametrize(
    "price",
    (
        "",
        "#N/A",
        "UNAVAILABLE",
        "not-a-number",
        "0",
        "-1",
    ),
)
def test_invalid_price_is_blocked(price: str) -> None:
    payload = _payload()
    payload["price"] = price

    with pytest.raises(ValueError):
        build_market_snapshot(
            payload,
            now=NOW,
        )


def test_google_finance_never_becomes_broker_live() -> None:
    result = build_market_snapshot(
        _payload(),
        now=NOW,
    )

    assert result["data_class"] != "LIVE_BROKER_DATA"


@pytest.mark.parametrize(
    "flag",
    (
        "generate_signal",
        "give_signal",
        "recommend_trade",
        "place_trade",
        "send_telegram",
        "send_whatsapp",
        "publish_price",
        "modify_google_sheet",
    ),
)
def test_sensitive_actions_are_blocked(
    flag: str,
) -> None:
    payload = _payload()
    payload[flag] = True

    with pytest.raises(PermissionError):
        run_market_data_agent(payload)


def test_runner_returns_verified_json(
    monkeypatch,
) -> None:
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW if tz is None else NOW.astimezone(tz)

    monkeypatch.setattr(
        "services.market_data_agent.datetime",
        FixedDateTime,
    )

    result = json.loads(
        run_market_data_agent(_payload())
    )

    assert result["symbol"] == "XAUUSD"
    assert result["price"] == "3345.20"
    assert result["signal_generated"] is False
