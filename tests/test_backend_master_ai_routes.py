"""Regression tests for Telegram webhook route registration."""

from __future__ import annotations

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
