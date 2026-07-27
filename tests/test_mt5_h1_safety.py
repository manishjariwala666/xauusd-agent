import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from services import mt5_h1_api
from services.mt5_h1_rate_limit import MT5RateLimiter
from services.mt5_h1_repository import InMemoryH1Repository


def build_client(monkeypatch) -> TestClient:
    monkeypatch.setenv("MT5_H1_INGEST_SECRET", "safe-test-secret")
    mt5_h1_api.repository = InMemoryH1Repository()
    mt5_h1_api.rate_limiter = MT5RateLimiter(max_requests=2)

    app = FastAPI()
    app.include_router(mt5_h1_api.router)
    return TestClient(app)


def test_ingestion_rate_limit_returns_429(monkeypatch):
    client = build_client(monkeypatch)

    headers = {
        "Content-Type": "application/json",
        "X-MT5-Signature": "invalid",
    }

    assert client.post(
        "/market-data/mt5/h1",
        content=b"{}",
        headers=headers,
    ).status_code == 403

    assert client.post(
        "/market-data/mt5/h1",
        content=b"{}",
        headers=headers,
    ).status_code == 403

    response = client.post(
        "/market-data/mt5/h1",
        content=b"{}",
        headers=headers,
    )

    assert response.status_code == 429


def test_source_files_do_not_log_raw_payload_or_secret():
    api_source = open(
        "services/mt5_h1_api.py",
        encoding="utf-8",
    ).read()

    bridge_source = open(
        "services/mt5_local_signing_bridge.py",
        encoding="utf-8",
    ).read()

    forbidden_log_patterns = [
        "logger.info(raw_body",
        "logger.debug(raw_body",
        "logger.info(secret",
        "logger.debug(secret",
        "print(secret",
        "print(raw_body",
    ]

    combined = api_source + bridge_source

    for pattern in forbidden_log_patterns:
        assert pattern not in combined


def test_no_trade_execution_route_is_defined():
    source = open(
        "services/mt5_h1_api.py",
        encoding="utf-8",
    ).read().lower()

    assert "@router.post(\"/trade" not in source
    assert "@router.post(\"/order" not in source
    assert "@router.post(\"/position" not in source
