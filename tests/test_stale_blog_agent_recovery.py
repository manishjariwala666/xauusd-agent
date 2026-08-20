from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from services import ai_agent_service as service


class _Result:
    def __init__(self, row=None):
        self.row = row

    def mappings(self):
        return self

    def first(self):
        return self.row


class _Session:
    def __init__(self, agent, run):
        self.agent = agent
        self.run = run
        self.statements = []

    def execute(self, statement, params=None):
        sql = str(statement)
        self.statements.append((sql, params or {}))
        if "FROM public.ai_agents" in sql and "FOR UPDATE" in sql:
            return _Result(self.agent)
        if "FROM public.ai_agent_runs" in sql and "FOR UPDATE" in sql:
            return _Result(self.run)
        return _Result()


def _scope(session):
    @contextmanager
    def scope():
        yield session

    return scope


def test_recovers_only_clearly_stale_blog_run_and_preserves_audit(monkeypatch):
    session = _Session(
        {"id": 1, "agent_key": "ai_blog_agent", "is_enabled": False, "status": "RUNNING"},
        {"id": 5482, "started_at": datetime.now(timezone.utc) - timedelta(days=30)},
    )
    monkeypatch.setattr(service, "session_scope", _scope(session))

    result = service.recover_stale_blog_agent_run_guarded(
        actor_id=7,
        request_id="req-stale",
    )

    assert result.recovered is True
    assert result.run_id == 5482
    assert result.status == "IDLE"
    assert any("UPDATE public.ai_agent_runs" in sql for sql, _ in session.statements)
    assert any("UPDATE public.ai_agents" in sql for sql, _ in session.statements)
    assert any("AI_BLOG_AGENT_STALE_RUN_RECOVERED" in sql for sql, _ in session.statements)
    assert all("DELETE" not in sql.upper() for sql, _ in session.statements)


def test_does_not_steal_active_blog_run(monkeypatch):
    session = _Session(
        {"id": 1, "agent_key": "ai_blog_agent", "is_enabled": True, "status": "RUNNING"},
        {"id": 9, "started_at": datetime.now(timezone.utc) - timedelta(minutes=10)},
    )
    monkeypatch.setattr(service, "session_scope", _scope(session))

    result = service.recover_stale_blog_agent_run_guarded(
        actor_id=7,
        request_id="req-active",
    )

    assert result.recovered is False
    assert result.run_id == 9
    assert not any("UPDATE public.ai_agent_runs" in sql for sql, _ in session.statements)
    assert not any("AI_BLOG_AGENT_STALE_RUN_RECOVERED" in sql for sql, _ in session.statements)


def test_worker_preflight_recovers_blog_state_before_start(monkeypatch):
    captured = {}

    def recover(**kwargs):
        captured.update(kwargs)
        return service.StaleAgentRecoveryResult(
            agent_key="ai_blog_agent",
            recovered=True,
            run_id=5482,
            previous_enabled=False,
            status="IDLE",
            reason="recovered",
        )

    monkeypatch.setattr(service, "recover_stale_blog_agent_run_guarded", recover)
    monkeypatch.setattr(service, "_start_run", lambda *_args, **_kwargs: service.AgentStartResult(None, "blocked by test"))

    succeeded, message = service.run_ai_agent("ai_blog_agent", None, None, {})

    assert succeeded is False
    assert message == "blocked by test"
    assert captured["actor_id"] is None
    assert captured["request_id"].startswith("worker-stale-recovery:")
