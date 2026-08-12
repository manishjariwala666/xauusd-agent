#!/usr/bin/env python3
"""Fail-closed database and migration readiness verification.

This helper reads a database URL from an environment variable, never prints
that value, and never applies migrations or changes database state.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
import os
import re
import sys
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError


LATEST_REQUIRED_MIGRATION = "020_automation_service_leads.sql"
_ENVIRONMENT_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")
_MIGRATION_NAME = re.compile(r"^[0-9]{3}_[a-z0-9_]+\.sql$")


class LaunchReadinessError(RuntimeError):
    """Raised when a launch-readiness requirement is not satisfied."""


def _normalized_database_url(database_url: str) -> URL:
    """Validate PostgreSQL configuration and select the installed psycopg driver."""
    try:
        parsed = make_url(database_url.strip())
    except ArgumentError as exc:
        raise LaunchReadinessError("Database configuration is invalid.") from exc
    if parsed.drivername not in {
        "postgresql",
        "postgresql+psycopg",
        "postgresql+psycopg2",
    }:
        raise LaunchReadinessError("Database configuration is invalid.")
    if not parsed.host or not parsed.database:
        raise LaunchReadinessError("Database configuration is invalid.")
    return parsed.set(drivername="postgresql+psycopg")


def verify_database_readiness(
    database_url: str,
    *,
    required_migration: str = LATEST_REQUIRED_MIGRATION,
    engine_factory: Callable[..., Any] = create_engine,
) -> None:
    """Verify connectivity and the required migration without writing data."""
    if not database_url.strip():
        raise LaunchReadinessError("Database configuration is missing.")
    if not _MIGRATION_NAME.fullmatch(required_migration):
        raise LaunchReadinessError("Required migration name is invalid.")

    engine: Any | None = None
    try:
        engine = engine_factory(
            _normalized_database_url(database_url),
            pool_pre_ping=True,
            connect_args={"connect_timeout": 5},
        )
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            applied = connection.execute(
                text(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM public.schema_migrations
                        WHERE name = :name
                    )
                    """
                ),
                {"name": required_migration},
            ).scalar_one()
    except Exception as exc:
        raise LaunchReadinessError(
            "Database connectivity or schema verification failed."
        ) from exc
    finally:
        if engine is not None:
            engine.dispose()

    if not applied:
        raise LaunchReadinessError("Required migration is not applied.")


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line interface."""
    parser = argparse.ArgumentParser(
        description=(
            "Verify PostgreSQL connectivity and the latest required migration "
            "without changing database state."
        )
    )
    parser.add_argument(
        "--database-env",
        default="DATABASE_URL",
        help="Environment variable containing the database URL (default: DATABASE_URL).",
    )
    parser.add_argument(
        "--required-migration",
        default=LATEST_REQUIRED_MIGRATION,
        help="Required schema_migrations record.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Describe checks without connecting to PostgreSQL.",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    engine_factory: Callable[..., Any] = create_engine,
) -> int:
    """Run fail-closed launch verification and return a process exit code."""
    args = build_parser().parse_args(argv)
    if not _ENVIRONMENT_NAME.fullmatch(args.database_env):
        print("Launch readiness verification failed.", file=sys.stderr)
        return 2
    if not _MIGRATION_NAME.fullmatch(args.required_migration):
        print("Launch readiness verification failed.", file=sys.stderr)
        return 2

    if args.dry_run:
        print(
            "DRY RUN: would verify the configured database, connectivity, "
            f"and migration {args.required_migration}; no database changes would occur."
        )
        return 0

    environment = os.environ if environ is None else environ
    database_url = str(environment.get(args.database_env, ""))
    try:
        verify_database_readiness(
            database_url,
            required_migration=args.required_migration,
            engine_factory=engine_factory,
        )
    except LaunchReadinessError:
        print("Launch readiness verification failed.", file=sys.stderr)
        return 1

    print("Database connectivity: OK")
    print(f"Required migration {args.required_migration}: OK")
    print("No database changes were made.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
