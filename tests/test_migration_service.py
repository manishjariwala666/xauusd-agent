"""Launch-readiness tests for ordered, transactional startup migrations."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

import pytest

from services import migration_service


EXPECTED_MIGRATIONS = (
    "002_market_signals_delivery.sql",
    "003_website_content_payment.sql",
    "004_admin_overview_metrics.sql",
    "005_ai_agents.sql",
    "006_production_agents.sql",
    "007_master_ai_orchestrator.sql",
    "008_content_system_extensions.sql",
    "008_master_ai_telegram_control.sql",
    "009_two_telegram_bots.sql",
    "010_admin_operations_extensions.sql",
    "011_command_mode_agent_policy.sql",
    "012_content_view_analytics.sql",
    "013_category_source_routing.sql",
    "014_admin_auth_foundation.sql",
    "015_admin_content_cms.sql",
    "016_admin_media_library.sql",
    "017_admin_seo_management.sql",
    "018_signals_admin.sql",
    "019_announcements_verified_results.sql",
    "020_automation_service_leads.sql",
)


class _Result:
    def __init__(self, value: Any = None) -> None:
        self.value = value

    def scalar_one_or_none(self) -> Any:
        return self.value

    def scalar_one(self) -> Any:
        return self.value


@dataclass
class _EngineState:
    applied: set[str] = field(default_factory=set)
    executed: list[str] = field(default_factory=list)
    locked: list[str] = field(default_factory=list)
    fail_on: str | None = None


class _Connection:
    def __init__(self, state: _EngineState) -> None:
        self.state = state

    def execute(self, statement: object, parameters: dict[str, Any] | None = None) -> _Result:
        query = str(statement)
        name = str((parameters or {}).get("name") or "")
        if "pg_advisory_xact_lock" in query:
            self.state.locked.append(name)
        if "SELECT 1 FROM public.schema_migrations" in query:
            return _Result(1 if name in self.state.applied else None)
        if "INSERT INTO public.schema_migrations" in query:
            self.state.applied.add(name)
        return _Result()

    def exec_driver_sql(self, sql: str) -> None:
        name = sql.removeprefix("SQL:")
        self.state.executed.append(name)
        if name == self.state.fail_on:
            raise RuntimeError("synthetic migration failure")


class _Transaction:
    def __init__(self, state: _EngineState) -> None:
        self.state = state
        self.snapshot: set[str] = set()

    def __enter__(self) -> _Connection:
        self.snapshot = set(self.state.applied)
        return _Connection(self.state)

    def __exit__(self, exc_type: object, *_: object) -> bool:
        if exc_type is not None:
            self.state.applied = self.snapshot
        return False


class _Engine:
    def __init__(self, state: _EngineState) -> None:
        self.state = state

    def begin(self) -> _Transaction:
        return _Transaction(self.state)


def _configure(monkeypatch: pytest.MonkeyPatch, state: _EngineState) -> None:
    monkeypatch.setattr(migration_service, "get_engine", lambda: _Engine(state))
    monkeypatch.setattr(
        migration_service, "_migration_sql", lambda name: f"SQL:{name}"
    )


def test_all_launch_migrations_are_registered_in_dependency_order() -> None:
    assert migration_service._AUTOMATIC_MIGRATIONS == EXPECTED_MIGRATIONS
    assert migration_service.LATEST_REQUIRED_MIGRATION == EXPECTED_MIGRATIONS[-1]


def test_each_migration_is_applied_exactly_once(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _EngineState()
    _configure(monkeypatch, state)
    migration_service.apply_pending_migrations()
    migration_service.apply_pending_migrations()
    assert state.executed == list(EXPECTED_MIGRATIONS)
    assert state.applied == set(EXPECTED_MIGRATIONS)
    assert state.locked == list(EXPECTED_MIGRATIONS) * 2


def test_failure_is_not_recorded_and_stops_later_migrations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failed = "015_admin_content_cms.sql"
    state = _EngineState(fail_on=failed)
    _configure(monkeypatch, state)
    with pytest.raises(RuntimeError, match="synthetic migration failure"):
        migration_service.apply_pending_migrations()
    assert failed not in state.applied
    assert state.executed[-1] == failed
    assert "016_admin_media_library.sql" not in state.executed


def test_transaction_wrappers_are_removed_before_engine_transaction() -> None:
    wrapped = "-- comment\nBEGIN;\nCREATE TABLE example(id int);\nCOMMIT;\n"
    unwrapped = migration_service._without_outer_transaction(wrapped)
    assert "CREATE TABLE example" in unwrapped
    assert "BEGIN;" not in unwrapped
    assert "COMMIT;" not in unwrapped


def test_all_registered_files_exist_and_have_safe_executable_sql() -> None:
    for name in EXPECTED_MIGRATIONS:
        sql = migration_service._migration_sql(name)
        assert sql
        assert not re.search(r"(?im)^\s*BEGIN\s*;\s*$", sql)
        assert not re.search(r"(?im)^\s*COMMIT\s*;\s*$", sql)


def test_required_schema_uses_latest_record_only() -> None:
    class Session:
        def __init__(self, value: bool) -> None:
            self.value = value
            self.parameters: dict[str, str] = {}

        def execute(self, _statement: object, parameters: dict[str, str]) -> _Result:
            self.parameters = parameters
            return _Result(self.value)

    incomplete = Session(False)
    assert not migration_service.required_schema_is_ready(incomplete)
    complete = Session(True)
    assert migration_service.required_schema_is_ready(complete)
    assert complete.parameters["name"] == "020_automation_service_leads.sql"
