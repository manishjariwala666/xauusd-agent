import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from services import mt5_local_signing_bridge


def payload():
    return {
        "symbol": "XAUUSD",
        "broker_symbol": "XAUUSDm",
        "broker_server": "LOCAL_TEST",
        "timeframe": "H1",
        "timestamp_utc": "2026-07-27T12:05:00+00:00",
        "candle_start_utc": "2026-07-27T12:00:00+00:00",
        "open": "4090.10",
        "high": "4098.50",
        "low": "4088.20",
        "close": "4095.75",
        "source_event_id": "local-bridge-test",
    }


def test_local_bridge_signs_exact_canonical_body(monkeypatch):
    monkeypatch.setenv(
        "MT5_H1_REMOTE_URL",
        "https://staging.example/market-data/mt5/h1",
    )
    monkeypatch.setenv("MT5_H1_INGEST_SECRET", "bridge-test-secret")

    captured = {}

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"status":"accepted"}'

    def fake_urlopen(request, timeout):
        captured["body"] = request.data
        captured["signature"] = request.headers["X-mt5-signature"]
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr(
        mt5_local_signing_bridge,
        "urlopen",
        fake_urlopen,
    )

    client = TestClient(mt5_local_signing_bridge.app)
    response = client.post("/local/mt5/h1", json=payload())

    assert response.status_code == 200
    assert response.json()["status"] == "forwarded"

    expected = hmac.new(
        b"bridge-test-secret",
        captured["body"],
        hashlib.sha256,
    ).hexdigest()

    assert captured["signature"] == expected
    assert json.loads(captured["body"]) == payload()


def test_bridge_rejects_non_h1_payload(monkeypatch):
    client = TestClient(mt5_local_signing_bridge.app)
    value = payload()
    value["timeframe"] = "M5"

    response = client.post("/local/mt5/h1", json=value)

    assert response.status_code == 400


def test_bridge_requires_https_remote(monkeypatch):
    monkeypatch.setenv(
        "MT5_H1_REMOTE_URL",
        "http://unsafe.example/market-data/mt5/h1",
    )
    monkeypatch.setenv("MT5_H1_INGEST_SECRET", "secret")

    client = TestClient(mt5_local_signing_bridge.app)
    response = client.post("/local/mt5/h1", json=payload())

    assert response.status_code == 503
