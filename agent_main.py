"""Legacy-compatible entry point for the production Signal Agent."""

from __future__ import annotations

from loguru import logger

from services.production_agents import run_signal_agent


def main() -> None:
    """Execute one real signal cycle without fallback or embedded secrets."""
    logger.info("Starting production Signal Agent cycle")
    result = run_signal_agent({})
    logger.info("Signal Agent completed: {}", result)


if __name__ == "__main__":
    main()
