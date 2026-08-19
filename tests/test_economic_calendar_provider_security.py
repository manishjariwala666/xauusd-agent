from datetime import datetime, timezone

import requests

from services.ai_agents.economic_calendar import provider


def test_trading_economics_key_is_sent_in_header_not_query(
    monkeypatch,
):
    monkeypatch.setenv(
        "TRADING_ECONOMICS_API_KEY",
        "secret-api-key",
    )

    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return []

    def fake_get(url, *, headers, params, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["params"] = params
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr(requests, "get", fake_get)

    result = provider.load_high_impact_events(
        now=datetime(
            2026, 8, 14, 12, 0,
            tzinfo=timezone.utc,
        ),
    )

    assert result == ()
    assert "secret-api-key" not in captured["url"]
    assert "c" not in captured["params"]
    assert captured["headers"] == {
        "Authorization": "secret-api-key"
    }


def test_trading_economics_http_error_is_sanitized(
    monkeypatch,
):
    monkeypatch.setenv(
        "TRADING_ECONOMICS_API_KEY",
        "secret-api-key",
    )

    class Response:
        def raise_for_status(self):
            raise requests.HTTPError(
                "401 https://example.invalid?c=secret-api-key"
            )

        def json(self):
            return []

    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: Response(),
    )

    try:
        provider.load_high_impact_events(
            now=datetime(
                2026, 8, 14, 12, 0,
                tzinfo=timezone.utc,
            ),
        )
    except RuntimeError as exc:
        message = str(exc)
    else:
        raise AssertionError("Expected RuntimeError")

    assert message == (
        "Trading Economics calendar request failed."
    )
    assert "secret-api-key" not in message
