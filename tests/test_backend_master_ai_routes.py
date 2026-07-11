"""Regression tests for Telegram webhook route registration."""

from __future__ import annotations

from fastapi.testclient import TestClient

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
