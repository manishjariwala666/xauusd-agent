import services.production_agents as production_agents


def test_run_signal_agent_shadow_uses_per_signal_delivery_gates(
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

    def monitor_targets(*args, **kwargs):
        calls["targets"] += 1
        return 0

    def monitor_stop_loss(*args, **kwargs):
        calls["stop_loss"] += 1
        return 0

    def publish_website(*args, **kwargs):
        calls["website"] += 1

    def deliver_whatsapp(*args, **kwargs):
        calls["whatsapp"] += 1

    monkeypatch.setattr(
        production_agents,
        "run_pipeline_once",
        fake_pipeline,
    )
    monkeypatch.setattr(
        production_agents._legacy,
        "_monitor_target_hits",
        monitor_targets,
    )
    monkeypatch.setattr(
        production_agents._legacy,
        "_monitor_stop_loss_hits",
        monitor_stop_loss,
    )
    monkeypatch.setattr(
        production_agents._legacy,
        "_publish_pending_website_signals",
        publish_website,
    )
    monkeypatch.setattr(
        production_agents._legacy,
        "_deliver_pending_whatsapp_signals",
        deliver_whatsapp,
    )

    result = production_agents.run_signal_agent({})

    assert calls["pipeline"] == 1
    assert calls["targets"] == 1
    assert calls["stop_loss"] == 1
    assert calls["website"] == 1
    assert calls["whatsapp"] == 1

    assert result == "Signal pipeline completed across configured channels."
