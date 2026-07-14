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
        return [
            {
                "id": 1,
                "slug": "gold",
                "content_type": "BLOG",
                "title": "Gold update",
                "body": "Full article body must stay out of list payloads.",
                "schema_jsonld": {"@type": "Article"},
            }
        ]

    monkeypatch.setattr(backend, "list_content", fake_list_content)
    monkeypatch.setattr(backend, "_public_content_cache", [])
    monkeypatch.setattr(backend, "_public_content_cache_at", 0.0)
    client = TestClient(app)

    listing = client.get("/public/content?content_type=BLOG&limit=5")
    detail = client.get("/public/content/gold")

    assert listing.status_code == 200
    assert detail.status_code == 200
    assert listing.json()["items"][0]["slug"] == "gold"
    assert "body" not in listing.json()["items"][0]
    assert "schema_jsonld" not in listing.json()["items"][0]
    assert detail.json()["item"]["slug"] == "gold"
    assert detail.json()["item"]["body"].startswith("Full article")
    assert calls == [{"public_only": True, "limit": 100}]


def test_public_content_cache_has_short_ttl_and_does_not_cache_signals(
    monkeypatch,
) -> None:
    content_calls: list[int] = []
    signal_calls: list[int] = []
    monkeypatch.setattr(backend, "_public_content_cache", [])
    monkeypatch.setattr(backend, "_public_content_cache_at", 0.0)
    monkeypatch.setattr(
        backend,
        "list_content",
        lambda **_kwargs: content_calls.append(1) or [{"slug": "gold"}],
    )
    monkeypatch.setattr(
        backend,
        "list_public_signals",
        lambda page=1, page_size=12: signal_calls.append(page_size) or {"items": []},
    )
    client = TestClient(app)

    assert client.get("/public/content").status_code == 200
    assert client.get("/public/content").status_code == 200
    assert client.get("/public/signals?limit=2").status_code == 200
    assert client.get("/public/signals?limit=2").status_code == 200

    assert content_calls == [1]
    assert signal_calls == [2, 2]
    assert backend.PUBLIC_CONTENT_CACHE_TTL_SECONDS == 60


def test_public_content_payloads_are_compressed(monkeypatch) -> None:
    monkeypatch.setattr(
        backend,
        "_public_content_cache",
        [
            {
                "id": index,
                "slug": f"gold-{index}",
                "content_type": "BLOG",
                "title": "Gold market research " * 20,
            }
            for index in range(10)
        ],
    )
    monkeypatch.setattr(backend, "_public_content_cache_at", backend.monotonic())
    client = TestClient(app)

    response = client.get(
        "/public/content?limit=10",
        headers={"Accept-Encoding": "gzip"},
    )

    assert response.status_code == 200
    assert response.headers.get("content-encoding") == "gzip"


def test_public_categories_and_signals_endpoints(monkeypatch) -> None:
    monkeypatch.setattr(
        backend,
        "list_categories",
        lambda public_only=True: [{"slug": "xauusd-signals"}],
    )
    monkeypatch.setattr(
        backend,
        "list_public_signals",
        lambda page=1, page_size=12: {"items": [{"symbol": "XAUUSD", "limit": page_size}]},
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
