"""Phase P6.0 schema and interface compatibility tests.

These tests are intentionally static. They verify additive migration shape and
service skeleton importability without touching the database or executing any
Master AI business logic.
"""

from __future__ import annotations

import importlib
from pathlib import Path

from services.migration_service import _AUTOMATIC_MIGRATIONS


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "migrations" / "007_master_ai_orchestrator.sql"


def _migration_sql() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def test_master_ai_migration_is_additive_and_ordered() -> None:
    sql = _migration_sql()
    assert "CREATE TABLE IF NOT EXISTS public.master_ai_tasks" in sql
    assert "CREATE TABLE IF NOT EXISTS public.master_ai_runs" in sql
    assert "CREATE TABLE IF NOT EXISTS public.master_ai_execution_steps" in sql
    assert "CREATE TABLE IF NOT EXISTS public.master_ai_execution_edges" in sql
    assert "CREATE TABLE IF NOT EXISTS public.master_ai_context_versions" in sql
    assert "CREATE TABLE IF NOT EXISTS public.master_ai_memory_entries" in sql
    assert "CREATE TABLE IF NOT EXISTS public.master_ai_agent_messages" in sql
    assert "CREATE TABLE IF NOT EXISTS public.master_ai_approvals" in sql
    assert "CREATE TABLE IF NOT EXISTS public.master_ai_events" in sql


def test_existing_agent_tables_only_receive_nullable_compatibility_columns() -> None:
    sql = _migration_sql()
    assert "ALTER TABLE public.ai_agent_runs" in sql
    assert "ADD COLUMN IF NOT EXISTS master_run_id BIGINT NULL" in sql
    assert "ADD COLUMN IF NOT EXISTS master_step_id BIGINT NULL" in sql
    assert "ALTER TABLE public.ai_agent_jobs" in sql
    assert "DROP TABLE" not in sql.upper()
    assert "TRUNCATE" not in sql.upper()
    assert "DELETE FROM public.ai_agents" not in sql
    assert "UPDATE public.ai_agents" not in sql


def test_master_ai_schema_uses_redacted_payload_fields() -> None:
    sql = _migration_sql()
    assert "input_payload_redacted" in sql
    assert "output_payload_redacted" in sql
    assert "context_redacted" in sql
    assert "data_redacted" in sql
    assert "payload_redacted" in sql
    assert "metadata_redacted" in sql
    assert "service_account" not in sql.lower()
    assert "private_key" not in sql.lower()
    assert "secret" not in sql.lower()
    assert "token" not in sql.lower()


def test_master_ai_tables_are_not_publicly_accessible() -> None:
    sql = _migration_sql()
    for table in (
        "master_ai_tasks",
        "master_ai_runs",
        "master_ai_execution_steps",
        "master_ai_execution_edges",
        "master_ai_context_versions",
        "master_ai_memory_entries",
        "master_ai_agent_messages",
        "master_ai_approvals",
        "master_ai_events",
    ):
        assert f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY" in sql
        assert f"REVOKE ALL ON TABLE public.{table} FROM anon, authenticated" in sql


def test_phase_p6_service_skeletons_import_without_side_effects() -> None:
    modules = [
        "services.master_orchestrator",
        "services.execution_planner",
        "services.execution_graph",
        "services.orchestration_memory",
        "services.shared_task_context",
        "services.agent_message_bus",
        "services.orchestration_notifications",
        "services.worker_agent_adapter",
    ]
    for module_name in modules:
        importlib.import_module(module_name)


def test_master_ai_migrations_are_in_automatic_startup_order() -> None:
    assert "007_master_ai_orchestrator.sql" in _AUTOMATIC_MIGRATIONS
    assert "008_master_ai_telegram_control.sql" in _AUTOMATIC_MIGRATIONS
    assert _AUTOMATIC_MIGRATIONS.index(
        "007_master_ai_orchestrator.sql"
    ) < _AUTOMATIC_MIGRATIONS.index("008_master_ai_telegram_control.sql")
    assert _AUTOMATIC_MIGRATIONS.index(
        "008_content_system_extensions.sql"
    ) < _AUTOMATIC_MIGRATIONS.index("010_admin_operations_extensions.sql")
    assert "011_command_mode_agent_policy.sql" in _AUTOMATIC_MIGRATIONS


def test_command_mode_policy_keeps_only_daily_signal_schedule() -> None:
    sql = (
        ROOT / "migrations" / "011_command_mode_agent_policy.sql"
    ).read_text(encoding="utf-8")

    assert "TIME '03:30'" in sql
    assert "Asia/Kolkata" in sql
    assert "scheduled_signal" in sql
    assert "a.agent_key <> 'signal_agent'" in sql
    assert "Cancelled by command-mode policy" in sql
