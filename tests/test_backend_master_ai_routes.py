"""Regression tests for Telegram webhook route registration."""

from __future__ import annotations

from fastapi.testclient import TestClient

import backend
from backend import app


def _route_has_method(path: str, method: str) -> bool:
    for route in app.routes:
        if getattr(route, "path", None) != path:
            continue
        methods = getattr(route, "methods", set()) or set()
        if method.upper() in methods:
            return True
    return False


def test_telegram_signal_and_master_routes_are_registered() -> None:
    assert _route_has_method("/webhooks/telegram", "POST")
    assert _route_has_method("/webhooks/telegram/master", "POST")


def test_search_indexing_can_be_blocked_without_database(monkeypatch) -> None:
    monkeypatch.setenv("BLOCK_SEARCH_INDEXING", "true")
    client = TestClient(app)

    robots = client.get("/robots.txt")
    health = client.get("/health")
    sitemap = client.get("/sitemap.xml")

    assert robots.status_code == 200
    assert "Disallow: /" in robots.text
    assert robots.headers["x-robots-tag"] == "noindex, nofollow, noarchive"
    assert health.headers["x-robots-tag"] == "noindex, nofollow, noarchive"
    assert "<urlset" in sitemap.text
    assert "<loc>" not in sitemap.text


def test_public_content_endpoints_only_request_public_rows(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_list_content(**kwargs):
        calls.append(kwargs)
        return [{"id": 1, "slug": "gold", "content_type": "BLOG"}]

    monkeypatch.setattr(backend, "list_content", fake_list_content)
    client = TestClient(app)

    listing = client.get("/public/content?content_type=BLOG&limit=5")
    detail = client.get("/public/content/gold")

    assert listing.status_code == 200
    assert detail.status_code == 200
    assert listing.json()["items"][0]["slug"] == "gold"
    assert detail.json()["item"]["slug"] == "gold"
    assert calls[0] == {
        "content_type": "BLOG",
        "public_only": True,
        "limit": 5,
    }
    assert calls[1] == {
        "public_only": True,
        "limit": 1,
        "exact_slug": "gold",
    }


def test_public_categories_and_signals_endpoints(monkeypatch) -> None:
    monkeypatch.setattr(
        backend,
        "list_categories",
        lambda public_only=True: [{"slug": "xauusd-signals"}],
    )
    monkeypatch.setattr(
        backend,
        "get_live_market_signals",
        lambda limit=12: [{"symbol": "XAUUSD", "limit": limit}],
    )
    client = TestClient(app)

    categories = client.get("/public/categories")
    signals = client.get("/public/signals?limit=3")

    assert categories.status_code == 200
    assert categories.json()["items"][0]["slug"] == "xauusd-signals"
    assert signals.status_code == 200
    assert signals.json()["items"][0] == {"symbol": "XAUUSD", "limit": 3}


def test_public_content_rejects_admin_or_unknown_types() -> None:
    client = TestClient(app)

    response = client.get("/public/content?content_type=MASTER_AI_EVENT")

    assert response.status_code == 400
