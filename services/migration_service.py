"""Idempotent, ordered database migrations for application startup."""

from __future__ import annotations

from pathlib import Path
import os
import re
from typing import Any

from loguru import logger
from sqlalchemy import text

from core.database import get_engine


_ROOT = Path(__file__).resolve().parents[1]
_AUTOMATIC_MIGRATIONS = (
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
LATEST_REQUIRED_MIGRATION = _AUTOMATIC_MIGRATIONS[-1]
MIGRATION_ALLOWLIST_ENV = "MIGRATION_ALLOWLIST"


def _selected_migrations() -> tuple[str, ...]:
    """Return the configured ordered migration subset, failing closed."""
    raw_allowlist = os.getenv(MIGRATION_ALLOWLIST_ENV)
    if raw_allowlist is None:
        return _AUTOMATIC_MIGRATIONS

    requested = {
        name.strip() for name in raw_allowlist.split(",") if name.strip()
    }
    if not requested:
        raise RuntimeError("MIGRATION_ALLOWLIST must contain a migration name.")

    unknown = requested.difference(_AUTOMATIC_MIGRATIONS)
    if unknown:
        raise RuntimeError("MIGRATION_ALLOWLIST contains an unapproved migration.")

    return tuple(name for name in _AUTOMATIC_MIGRATIONS if name in requested)


def _without_outer_transaction(sql: str) -> str:
    """Remove migration-file wrappers; engine.begin owns the transaction."""
    normalized = re.sub(r"(?im)^\s*BEGIN\s*;\s*$", "", sql, count=1)
    commit_matches = list(re.finditer(r"(?im)^\s*COMMIT\s*;\s*$", normalized))
    if commit_matches:
        match = commit_matches[-1]
        normalized = normalized[: match.start()] + normalized[match.end() :]
    return normalized.strip()


def _migration_sql(name: str) -> str:
    path = _ROOT / "migrations" / name
    return _without_outer_transaction(path.read_text(encoding="utf-8"))


def required_schema_is_ready(session: Any) -> bool:
    """Return whether the latest launch-required migration is recorded."""
    return bool(
        session.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1 FROM public.schema_migrations WHERE name = :name
                )
                """
            ),
            {"name": LATEST_REQUIRED_MIGRATION},
        ).scalar_one()
    )


def apply_pending_migrations() -> None:
    """Apply approved backend migrations transactionally once."""
    selected_migrations = _selected_migrations()
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS public.schema_migrations (
                    name TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )
    for name in selected_migrations:
        sql = _migration_sql(name)
        with engine.begin() as connection:
            # API, worker, and web may start together. The transaction-scoped
            # lock serializes the same migration across processes.
            connection.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:name, 0))"),
                {"name": name},
            )
            applied = connection.execute(
                text(
                    "SELECT 1 FROM public.schema_migrations WHERE name = :name"
                ),
                {"name": name},
            ).scalar_one_or_none()
            if applied:
                continue
            connection.exec_driver_sql(sql)
            connection.execute(
                text(
                    "INSERT INTO public.schema_migrations (name) VALUES (:name)"
                ),
                {"name": name},
            )
        logger.info("Database migration applied: {}", name)
