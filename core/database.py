"""SQLAlchemy engine and transaction helpers."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, URL, make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import Session, sessionmaker

from config import ConfigurationError, get_settings


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def normalize_database_url(raw_url: str) -> URL:
    """Return a validated SQLAlchemy URL using the psycopg v3 dialect."""
    candidate = raw_url.strip()
    if candidate.startswith("postgres://"):
        candidate = "postgresql://" + candidate.removeprefix("postgres://")

    try:
        parsed = make_url(candidate)
    except ArgumentError as exc:
        raise ConfigurationError("DATABASE_URL is not a valid URL.") from exc

    supported_drivers = {
        "postgresql",
        "postgresql+psycopg",
        "postgresql+psycopg2",
    }
    if parsed.drivername not in supported_drivers:
        raise ConfigurationError(
            "DATABASE_URL must use a PostgreSQL scheme."
        )
    if not parsed.host or not parsed.database:
        raise ConfigurationError(
            "DATABASE_URL must include a database host and name."
        )

    # Explicitly selecting psycopg prevents SQLAlchemy's PostgreSQL default
    # from importing the legacy psycopg2 driver on Streamlit Cloud.
    return parsed.set(drivername="postgresql+psycopg")


def get_engine() -> Engine:
    """Create a pooled PostgreSQL engine lazily."""
    global _engine, _session_factory
    if _engine is None:
        settings = get_settings()
        database_url = normalize_database_url(settings.database_url)
        _engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=1_800,
            pool_size=5,
            max_overflow=10,
            connect_args={"connect_timeout": 10},
        )
        _session_factory = sessionmaker(
            bind=_engine,
            autoflush=False,
            expire_on_commit=False,
            class_=Session,
        )
    return _engine


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional session with rollback on failure."""
    global _session_factory
    get_engine()
    if _session_factory is None:
        raise RuntimeError("Database session factory was not initialized.")

    session = _session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
