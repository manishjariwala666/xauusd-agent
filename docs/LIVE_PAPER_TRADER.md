# Live XAUUSD paper trader

The paper trader reads the newest row from the private Google Sheet worksheet
`xauusd_calculation_parameters`. The row must contain `i_useAggressive`,
`valBuyLevel`, `valSellLevel`, and at least one `lvlT1`…`lvlT6` or
`lvlS1`…`lvlS6` value. Optional stop columns are `valBuyStop` and
`valSellStop` (with `buyStop`/`sellStop` and `stopBuy`/`stopSell` aliases).

Run one safe check:

```bash
PAPER_TRADING=true python scripts/run_live_paper_trader.py --once
```

Run continuously with terminal logs and macOS notifications:

```bash
PAPER_TRADING=true python scripts/run_live_paper_trader.py --interval 60
```

The monitor refreshes the Sheet row every tick, fetches a live GoldAPI quote
with Yahoo Finance fallback, and records `WATCH`, `PAPER OPEN`, `PAPER TARGET`,
`PAPER STOP`, and `PAPER HOLD` events through Loguru. It never calls a broker
and never places a real order. A provider 401/403 raises an authorization block
and leaves the paper position unchanged; missing rows, rate limits, and network
errors only make that tick wait and the loop continues.

Keep `PAPER_TRADING=true` explicit in the runtime environment. The command
exits if paper mode is disabled.
