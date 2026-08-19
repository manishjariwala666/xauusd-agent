from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json

import pytest

from services.mt5_h1_market_data import (
    MT5H1AuthenticationError,
    MT5H1DuplicateError,
    MT5H1ValidationError,
    calculate_signature,
    ingest_h1_payload,
    sheet_response,
)
from services.mt5_h1_repository import H1Candle, InMemoryH1Repository


SECRET = "local-test-secret-only"
NOW = datetime(2026, 7, 27, 10, 30, tzinfo=timezone.utc)


def payload(**overrides):
    value = {
        "symbol": "XAUUSD",
        "broker_symbol": "XAUUSDm",
        "broker_server": "Local-Test-Server",
        "timeframe": "H1",
        "timestamp_utc": NOW.isoformat(),
        "candle_start_utc": NOW.replace(minute=0).isoformat(),
        "open": "4090.10",
        "high": "4098.50",
        "low": "4088.20",
        "close": "4095.75",
        "source_event_id": "xauusd-h1-20260727T1000-v1",
    }
    value.update(overrides)
    return value


def encoded(value):
    return json.dumps(
        value,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()


def ingest(value, repository=None, now=NOW, signature=None):
    repo = repository or InMemoryH1Repository()
    raw = encoded(value)
    supplied_signature = signature or calculate_signature(SECRET, raw)

    return ingest_h1_payload(
        raw_body=raw,
        signature=supplied_signature,
        secret=SECRET,
        repository=repo,
        now=now,
    )


def test_valid_signed_h1_payload_is_accepted():
    candle = ingest(payload())

    assert candle.symbol == "XAUUSD"
    assert candle.broker_symbol == "XAUUSDM"
    assert candle.high == Decimal("4098.50")
    assert candle.source == "MT5"


def test_invalid_signature_is_rejected():
    with pytest.raises(MT5H1AuthenticationError):
        ingest(payload(), signature="bad-signature")


def test_stale_payload_is_rejected():
    old = NOW - timedelta(minutes=20)

    with pytest.raises(MT5H1ValidationError, match="Stale"):
        ingest(payload(timestamp_utc=old.isoformat()))


def test_duplicate_event_is_blocked():
    repository = InMemoryH1Repository()
    value = payload()

    ingest(value, repository=repository)

    with pytest.raises(MT5H1DuplicateError):
        ingest(value, repository=repository)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("symbol", "BTCUSD"),
        ("broker_symbol", "EURUSD"),
        ("timeframe", "M5"),
    ],
)
def test_wrong_symbol_or_timeframe_is_rejected(field, value):
    with pytest.raises(MT5H1ValidationError):
        ingest(payload(**{field: value}))


def test_sheet_response_contains_only_mt5_source():
    candle = ingest(payload())

    response = sheet_response(candle, fresh=True)

    assert response["timeframe"] == "H1"
    assert response["source"] == "MT5"
    assert response["fresh"] is True
    assert response["open"] == "4090.10"
    assert response["high"] == "4098.50"
    assert response["low"] == "4088.20"
    assert response["close"] == "4095.75"
    assert "fallback" not in response
