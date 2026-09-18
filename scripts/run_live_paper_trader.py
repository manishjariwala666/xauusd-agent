#!/usr/bin/env python3
"""Run the Google Sheet → live XAUUSD → paper-trade monitor."""

from __future__ import annotations

import argparse
import os

from loguru import logger

from config import get_settings
from services.live_paper_trader import (
    GoogleSheetParameterSource,
    LiveXauUsdPriceSource,
    MacOSNotifier,
    PaperTrader,
    run_forever,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval", type=int, default=60, help="Seconds between checks")
    parser.add_argument("--sheet-tab", default="xauusd_calculation_parameters")
    parser.add_argument("--once", action="store_true", help="Run one safe monitoring tick")
    args = parser.parse_args()

    if os.getenv("PAPER_TRADING", "true").lower() not in {"1", "true", "yes", "on"}:
        logger.error("PAPER_TRADING must be enabled; no order execution is supported.")
        return 2
    settings = get_settings()
    trader = PaperTrader(
        parameter_source=GoogleSheetParameterSource(tab_name=args.sheet_tab),
        price_source=LiveXauUsdPriceSource(
            goldapi_key=settings.goldapi_key,
            symbol=settings.xauusd_symbol,
        ),
        notifier=MacOSNotifier(),
    )
    if args.once:
        trader.tick()
        return 0
    run_forever(trader, interval_seconds=max(1, args.interval))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
