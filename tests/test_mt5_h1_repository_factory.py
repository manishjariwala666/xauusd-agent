from services import mt5_h1_repository_factory
from services.mt5_h1_postgres_repository import PostgresH1Repository
from services.mt5_h1_repository import InMemoryH1Repository


def test_repository_defaults_to_memory_without_database(monkeypatch):
    monkeypatch.delenv("MT5_H1_REPOSITORY_BACKEND", raising=False)

    repository = mt5_h1_repository_factory.build_mt5_h1_repository()

    assert isinstance(repository, InMemoryH1Repository)


def test_unknown_repository_backend_fails_safe_to_memory(monkeypatch):
    monkeypatch.setenv("MT5_H1_REPOSITORY_BACKEND", "unknown")

    repository = mt5_h1_repository_factory.build_mt5_h1_repository()

    assert isinstance(repository, InMemoryH1Repository)


def test_postgres_repository_can_be_constructed_without_querying_tables(
    monkeypatch,
):
    monkeypatch.setenv("MT5_H1_REPOSITORY_BACKEND", "postgres")

    repository = mt5_h1_repository_factory.build_mt5_h1_repository()

    assert isinstance(repository, PostgresH1Repository)
