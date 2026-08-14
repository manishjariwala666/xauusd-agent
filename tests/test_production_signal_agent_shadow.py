import services.production_agents as production_agents


def test_run_signal_agent_shadow_blocks_all_post_pipeline_delivery(
    monkeypatch,
):
    monkeypatch.setenv(
        "CAPTAIN_SIGNAL_SHADOW_GATE",
        "1",
    )

    calls = {
        "pipeline": 0,
        "targets": 0,
        "stop_loss": 0,
        "website": 0,
        "whatsapp": 0,
    }

    class FakeMarketData:
        pass

    class FakeTelegram:
        pass

    monkeypatch.setattr(
        production_agents,
        "get_settings",
        lambda: type(
            "Settings",
            (),
            {
                "supabase_url": "https://example.supabase.co",
                "supabase_key": "test-key",
            },
        )(),
    )

    monkeypatch.setattr(
        production_agents,
        "create_client",
        lambda *args, **kwargs: object(),
    )

    monkeypatch.setattr(
        production_agents,
        "GoogleSheetsService",
        lambda: object(),
    )

    monkeypatch.setattr(
        production_agents,
        "MarketDataService",
        lambda supabase: FakeMarketData(),
    )

    monkeypatch.setattr(
        production_agents,
        "TelegramService",
        lambda supabase: FakeTelegram(),
    )

    def fake_pipeline(*args, **kwargs):
        calls["pipeline"] += 1

    def fail_targets(*args, **kwargs):
        calls["targets"] += 1
        raise AssertionError(
            "Target-hit monitor must not run in Captain shadow mode"
        )

    def fail_stop_loss(*args, **kwargs):
        calls["stop_loss"] += 1
        raise AssertionError(
            "Stop-loss monitor must not run in Captain shadow mode"
        )

    def fail_website(*args, **kwargs):
        calls["website"] += 1
        raise AssertionError(
            "Website publishing must not run in Captain shadow mode"
        )

    def fail_whatsapp(*args, **kwargs):
        calls["whatsapp"] += 1
        raise AssertionError(
            "WhatsApp delivery must not run in Captain shadow mode"
        )

    monkeypatch.setattr(
        production_agents,
        "run_pipeline_once",
        fake_pipeline,
    )
    monkeypatch.setattr(
        production_agents,
        "_monitor_target_hits",
        fail_targets,
    )
    monkeypatch.setattr(
        production_agents,
        "_monitor_stop_loss_hits",
        fail_stop_loss,
    )
    monkeypatch.setattr(
        production_agents,
        "_publish_pending_website_signals",
        fail_website,
    )
    monkeypatch.setattr(
        production_agents,
        "_deliver_pending_whatsapp_signals",
        fail_whatsapp,
    )

    result = production_agents.run_signal_agent({})

    assert calls["pipeline"] == 1
    assert calls["targets"] == 0
    assert calls["stop_loss"] == 0
    assert calls["website"] == 0
    assert calls["whatsapp"] == 0

    assert "Captain shadow mode" in result
    assert "all outbound delivery blocked" in result
