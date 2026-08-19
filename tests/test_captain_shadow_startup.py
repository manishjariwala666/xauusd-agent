import os

import backend


def _shadow_enabled() -> bool:
    return os.getenv(
        "CAPTAIN_SIGNAL_SHADOW_GATE",
        "",
    ).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def test_shadow_env_parser(monkeypatch):
    monkeypatch.setenv(
        "CAPTAIN_SIGNAL_SHADOW_GATE",
        "1",
    )

    assert _shadow_enabled() is True


def test_normal_mode_parser(monkeypatch):
    monkeypatch.delenv(
        "CAPTAIN_SIGNAL_SHADOW_GATE",
        raising=False,
    )

    assert _shadow_enabled() is False
