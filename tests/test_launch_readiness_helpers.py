"""Focused tests for fail-closed production launch helpers."""

from __future__ import annotations

from pathlib import Path

from scripts import verify_launch_readiness


ROOT = Path(__file__).resolve().parents[1]


class _Result:
    def __init__(self, value: object) -> None:
        self.value = value

    def scalar_one(self) -> object:
        return self.value


class _Connection:
    def __init__(self, migration_applied: bool) -> None:
        self.migration_applied = migration_applied
        self.calls = 0

    def __enter__(self) -> "_Connection":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def execute(self, _statement: object, _parameters: object = None) -> _Result:
        self.calls += 1
        return _Result(1 if self.calls == 1 else self.migration_applied)


class _Engine:
    def __init__(self, migration_applied: bool = True) -> None:
        self.connection = _Connection(migration_applied)
        self.disposed = False

    def connect(self) -> _Connection:
        return self.connection

    def dispose(self) -> None:
        self.disposed = True


def test_dry_run_does_not_create_database_engine(capsys) -> None:
    called = False

    def factory(*_args: object, **_kwargs: object) -> object:
        nonlocal called
        called = True
        raise AssertionError("dry-run must not connect")

    result = verify_launch_readiness.main(
        ["--dry-run"],
        environ={},
        engine_factory=factory,
    )
    assert result == 0
    assert not called
    assert "no database changes would occur" in capsys.readouterr().out.lower()


def test_missing_configuration_fails_closed_without_leaking_details(capsys) -> None:
    result = verify_launch_readiness.main([], environ={})
    captured = capsys.readouterr()
    assert result == 1
    assert captured.out == ""
    assert captured.err.strip() == "Launch readiness verification failed."


def test_connectivity_and_latest_migration_pass() -> None:
    engine = _Engine(migration_applied=True)
    result = verify_launch_readiness.main(
        [],
        environ={"DATABASE_URL": "postgresql://local@127.0.0.1/local"},
        engine_factory=lambda *_args, **_kwargs: engine,
    )
    assert result == 0
    assert engine.connection.calls == 2
    assert engine.disposed


def test_missing_latest_migration_fails_closed(capsys) -> None:
    engine = _Engine(migration_applied=False)
    result = verify_launch_readiness.main(
        [],
        environ={"DATABASE_URL": "postgresql://local@127.0.0.1/local"},
        engine_factory=lambda *_args, **_kwargs: engine,
    )
    assert result == 1
    assert engine.disposed
    assert capsys.readouterr().err.strip() == "Launch readiness verification failed."


def test_non_postgresql_configuration_is_rejected(capsys) -> None:
    result = verify_launch_readiness.main(
        [],
        environ={"DATABASE_URL": "sqlite:///local.db"},
        engine_factory=lambda *_args, **_kwargs: _Engine(),
    )
    assert result == 1
    assert capsys.readouterr().err.strip() == "Launch readiness verification failed."


def test_database_errors_do_not_expose_connection_values(capsys) -> None:
    sensitive_marker = "do-not-print-this-value"

    def factory(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError(sensitive_marker)

    result = verify_launch_readiness.main(
        [],
        environ={"DATABASE_URL": "postgresql://local@127.0.0.1/local"},
        engine_factory=factory,
    )
    output = capsys.readouterr()
    assert result == 1
    assert sensitive_marker not in output.out
    assert sensitive_marker not in output.err


def test_backup_helper_is_read_only_and_fail_closed() -> None:
    source = (ROOT / "scripts/verify_backup.sh").read_text(encoding="utf-8")
    assert "set -euo pipefail" in source
    assert 'pg_restore --list "$BACKUP_FILE"' in source
    assert "pg_dump" not in source
    assert "psql" not in source
    assert "pg_restore --dbname" not in source
    assert "BACKUP_FILE is not configured" in source
