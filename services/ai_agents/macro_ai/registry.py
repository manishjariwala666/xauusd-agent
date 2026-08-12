"""Approved market instruments and XAUUSD directional relationships."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class MacroInstrument:
    symbol: str
    label: str
    weight: Decimal
    inverse_to_gold: bool


INSTRUMENTS: tuple[MacroInstrument, ...] = (
    MacroInstrument("DXY", "US Dollar Index", Decimal("0.25"), True),
    MacroInstrument("US10Y", "US 10Y Yield", Decimal("0.20"), True),
    MacroInstrument("US2Y", "US 2Y Yield", Decimal("0.10"), True),
    MacroInstrument("VIX", "Volatility Index", Decimal("0.10"), False),
    MacroInstrument("XAGUSD", "Silver", Decimal("0.10"), False),
    MacroInstrument("SPX500", "S&P 500", Decimal("0.07"), True),
    MacroInstrument("US30", "Dow Jones", Decimal("0.05"), True),
    MacroInstrument("NASDAQ100", "Nasdaq 100", Decimal("0.05"), True),
    MacroInstrument("USOIL", "Crude Oil", Decimal("0.05"), False),
    MacroInstrument("BTCUSD", "Bitcoin", Decimal("0.03"), True),
)
