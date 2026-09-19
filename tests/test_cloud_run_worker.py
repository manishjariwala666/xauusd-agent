import cloud_run_worker


def test_cloud_run_worker_processes_one_job(monkeypatch):
    seen = {"claims": 0, "finish": [], "runs": []}

    monkeypatch.setattr(cloud_run_worker, "_apply_startup_migrations", lambda: None)
    monkeypatch.setattr(cloud_run_worker, "heartbeat", lambda worker_id: None)
    monkeypatch.setattr(cloud_run_worker, "enqueue_due_schedules", lambda: 2)

    def claim(_worker_id):
        seen["claims"] += 1
        if seen["claims"] == 1:
            return {
                "id": 10,
                "agent_key": "signal_agent",
                "payload": {"source": "test"},
                "triggered_by": None,
            }
        return None

    monkeypatch.setattr(cloud_run_worker, "claim_next_job", claim)
    monkeypatch.setattr(cloud_run_worker, "_start_agent_run", lambda key, who: 77)
    monkeypatch.setattr(
        cloud_run_worker,
        "finish_job",
        lambda job_id, success, error=None: seen["finish"].append(
            (job_id, success, error)
        ),
    )
    monkeypatch.setattr(
        cloud_run_worker,
        "_finish_agent_run",
        lambda *args: seen["runs"].append(args),
    )
    monkeypatch.setitem(
        cloud_run_worker.RUNNERS,
        "signal_agent",
        lambda payload: "cycle-ok",
    )

    assert cloud_run_worker.run_once() == (1, 0)
    assert seen["finish"] == [(10, True, None)]
    assert seen["runs"][0][0:3] == (77, "signal_agent", True)


def test_cloud_run_worker_records_failure_and_exits_non_looping(monkeypatch):
    claims = iter(
        [
            {
                "id": 11,
                "agent_key": "signal_agent",
                "payload": {},
                "triggered_by": None,
            },
            None,
        ]
    )
    finished = []

    monkeypatch.setattr(cloud_run_worker, "_apply_startup_migrations", lambda: None)
    monkeypatch.setattr(cloud_run_worker, "heartbeat", lambda worker_id: None)
    monkeypatch.setattr(cloud_run_worker, "enqueue_due_schedules", lambda: 0)
    monkeypatch.setattr(cloud_run_worker, "claim_next_job", lambda worker_id: next(claims))
    monkeypatch.setattr(cloud_run_worker, "_start_agent_run", lambda key, who: 88)
    monkeypatch.setattr(
        cloud_run_worker,
        "finish_job",
        lambda job_id, success, error=None: finished.append((job_id, success)),
    )
    monkeypatch.setattr(cloud_run_worker, "_finish_agent_run", lambda *args: None)

    def fail(_payload):
        raise RuntimeError("boom")

    monkeypatch.setitem(cloud_run_worker.RUNNERS, "signal_agent", fail)

    assert cloud_run_worker.run_once() == (1, 1)
    assert finished == [(11, False)]
