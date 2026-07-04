"""SQLAlchemy engine and transaction helpers."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from config import get_settings


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Create a pooled PostgreSQL engine lazily."""
    global _engine, _session_factory
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_recycle=1_800,
            pool_size=5,
            max_overflow=10,
            future=True,
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
