"""Small idempotent migration runner for the Render backend."""

from __future__ import annotations

from pathlib import Path

from loguru import logger
from sqlalchemy import text

from core.database import get_engine


_ROOT = Path(__file__).resolve().parents[1]
_AUTOMATIC_MIGRATIONS = (
    "002_market_signals_delivery.sql",
    "003_website_content_payment.sql",
    "005_ai_agents.sql",
    "006_production_agents.sql",
    "007_master_ai_orchestrator.sql",
    "008_content_system_extensions.sql",
    "008_master_ai_telegram_control.sql",
    "009_two_telegram_bots.sql",
    "010_admin_operations_extensions.sql",
)


def apply_pending_migrations() -> None:
    """Apply approved backend migrations transactionally once."""
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
    for name in _AUTOMATIC_MIGRATIONS:
        path = _ROOT / "migrations" / name
        sql = (
            path.read_text(encoding="utf-8")
            .replace("\nBEGIN;\n", "\n")
            .replace("\nCOMMIT;\n", "\n")
        )
        with engine.begin() as connection:
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
