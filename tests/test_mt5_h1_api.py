from datetime import datetime, timezone
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from services import mt5_h1_api
from services.mt5_h1_market_data import calculate_signature
from services.mt5_h1_repository import InMemoryH1Repository


SECRET = "local-api-test-secret"
NOW = datetime.now(timezone.utc).replace(microsecond=0)


def build_app(monkeypatch) -> TestClient:
    monkeypatch.setenv("MT5_H1_INGEST_SECRET", SECRET)
    mt5_h1_api.repository = InMemoryH1Repository()

    app = FastAPI()
    app.include_router(mt5_h1_api.router)

    return TestClient(app)


def payload(event_id="mt5-h1-api-test-1"):
    return {
        "symbol": "XAUUSD",
        "broker_symbol": "XAUUSDm",
        "broker_server": "Local-Test-Server",
        "timeframe": "H1",
        "timestamp_utc": NOW.isoformat(),
        "candle_start_utc": NOW.replace(
            minute=0,
            second=0,
            microsecond=0,
        ).isoformat(),
        "open": "4090.10",
        "high": "4098.50",
        "low": "4088.20",
        "close": "4095.75",
        "source_event_id": event_id,
    }


def signed_body(value):
    raw = json.dumps(
        value,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()

    return raw, calculate_signature(SECRET, raw)


def test_signed_h1_endpoint_accepts_payload(monkeypatch):
    client = build_app(monkeypatch)
    raw, signature = signed_body(payload())

    response = client.post(
        "/market-data/mt5/h1",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-MT5-Signature": signature,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    assert response.json()["timeframe"] == "H1"


def test_invalid_signature_is_forbidden(monkeypatch):
    client = build_app(monkeypatch)
    raw, _ = signed_body(payload())

    response = client.post(
        "/market-data/mt5/h1",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-MT5-Signature": "invalid",
        },
    )

    assert response.status_code == 403


def test_duplicate_event_returns_conflict(monkeypatch):
    client = build_app(monkeypatch)
    raw, signature = signed_body(payload())

    first = client.post(
        "/market-data/mt5/h1",
        content=raw,
        headers={"X-MT5-Signature": signature},
    )
    second = client.post(
        "/market-data/mt5/h1",
        content=raw,
        headers={"X-MT5-Signature": signature},
    )

    assert first.status_code == 200
    assert second.status_code == 409


def test_latest_endpoint_returns_complete_h1_without_source_mixing(monkeypatch):
    client = build_app(monkeypatch)
    raw, signature = signed_body(payload())

    client.post(
        "/market-data/mt5/h1",
        content=raw,
        headers={"X-MT5-Signature": signature},
    )

    response = client.get("/market-data/mt5/h1/latest")

    assert response.status_code == 200
    result = response.json()
    assert result["source"] == "MT5"
    assert result["open"] == "4090.10"
    assert result["high"] == "4098.50"
    assert result["low"] == "4088.20"
    assert result["close"] == "4095.75"


def test_no_trade_execution_route_exists(monkeypatch):
    client = build_app(monkeypatch)

    paths = {
        path
        for route in client.app.routes
        if (path := getattr(route, "path", None))
    }

    assert not any(
        word in path.lower()
        for path in paths
        for word in ("trade", "order", "position", "execute")
    )
