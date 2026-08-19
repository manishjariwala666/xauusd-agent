"""Safe MT5 repository selection without migration side effects."""

from __future__ import annotations

import os

from loguru import logger

from services.mt5_h1_postgres_repository import PostgresH1Repository
from services.mt5_h1_repository import H1Repository, InMemoryH1Repository


def build_mt5_h1_repository() -> H1Repository:
    backend = os.getenv(
        "MT5_H1_REPOSITORY_BACKEND",
        "memory",
    ).strip().lower()

    if backend == "postgres":
        logger.info("MT5 H1 repository backend selected: postgres")
        return PostgresH1Repository()

    if backend != "memory":
        logger.warning(
            "Unknown MT5 H1 repository backend; using memory safely."
        )

    return InMemoryH1Repository()
