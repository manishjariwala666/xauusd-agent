"""Deterministic macro scoring. No AI provider or trade execution is used."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from .models import (
    GoldBias,
    MacroAssessment,
    MacroDriverScore,
    MarketDirection,
    MarketSnapshot,
)
from .registry import INSTRUMENTS


def _direction_score(
    direction: MarketDirection,
    *,
    inverse_to_gold: bool,
) -> Decimal:
    if direction == MarketDirection.FLAT:
        return Decimal("0")

    raw = Decimal("1") if direction == MarketDirection.UP else Decimal("-1")
    return -raw if inverse_to_gold else raw


def assess_macro_bias(
    snapshots: tuple[MarketSnapshot, ...],
) -> MacroAssessment:
    by_symbol = {item.symbol.upper(): item for item in snapshots}
    drivers: list[MacroDriverScore] = []
    conflicts: list[str] = []
    total = Decimal("0")
    used = 0

    for instrument in INSTRUMENTS:
        snapshot = by_symbol.get(instrument.symbol)

        if snapshot is None:
            conflicts.append(f"{instrument.symbol} data missing")
            continue

        normalized = _direction_score(
            snapshot.direction,
            inverse_to_gold=instrument.inverse_to_gold,
        )

        contribution = (
            normalized * instrument.weight
        ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        total += contribution
        used += 1

        drivers.append(
            MacroDriverScore(
                symbol=instrument.symbol,
                weight=instrument.weight,
                normalized_score=normalized,
                contribution=contribution,
                rationale=(
                    f"{instrument.label} {snapshot.direction.value}; "
                    f"{'inverse' if instrument.inverse_to_gold else 'direct'} "
                    "gold relationship applied."
                ),
            )
        )

    total = total.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    if total >= Decimal("0.20"):
        bias = GoldBias.BUY
    elif total <= Decimal("-0.20"):
        bias = GoldBias.SELL
    else:
        bias = GoldBias.NEUTRAL

    confidence = min(
        100,
        max(
            0,
            int(
                (
                    abs(total) * Decimal("100")
                    + Decimal(used * 3)
                ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            ),
        ),
    )

    observed_at = max(item.observed_at for item in snapshots)

    return MacroAssessment(
        bias=bias,
        confidence=confidence,
        total_score=total,
        observed_at=observed_at,
        drivers=tuple(drivers),
        conflicts=tuple(conflicts),
        source_count=used,
    )
