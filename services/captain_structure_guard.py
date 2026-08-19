"""Deterministic structural safety checks layered on Captain observations."""

from __future__ import annotations

from dataclasses import dataclass

from services.captain_ai_runtime import CaptainObservedRun


@dataclass(frozen=True)
class CaptainStructureGuardResult:
    blocked: bool
    reason: str


def evaluate_captain_structure(observed: CaptainObservedRun | None) -> CaptainStructureGuardResult:
    """Block ambiguous two-sided session sweeps.

    A session that has already traded at/below Buy Base and at/above Sell Base
    has swept both directional trigger zones. In that state a later simple base
    cross is not enough evidence for a fresh directional signal; Captain/Shadow
    must wait for a new session or stronger explicit confirmation upstream.
    """
    if observed is None:
        return CaptainStructureGuardResult(False, "No observed Captain context.")

    if (
        observed.day_low is None
        or observed.day_high is None
        or observed.buy_base is None
        or observed.sell_base is None
    ):
        return CaptainStructureGuardResult(
            True,
            "Session structure incomplete; high/low or Buy/Sell Base unavailable.",
        )

    if observed.buy_base >= observed.sell_base:
        return CaptainStructureGuardResult(
            True,
            "Session structure invalid: Buy Base must remain below Sell Base.",
        )

    swept_buy_side = observed.day_low <= observed.buy_base
    swept_sell_side = observed.day_high >= observed.sell_base

    if swept_buy_side and swept_sell_side:
        return CaptainStructureGuardResult(
            True,
            (
                "Two-sided session sweep detected: price traded through both "
                f"Buy Base ({observed.buy_base}) and Sell Base ({observed.sell_base}). "
                "Base-cross alone is not valid confirmation; WAIT required."
            ),
        )

    return CaptainStructureGuardResult(False, "Session structure is one-sided or unresolved.")
