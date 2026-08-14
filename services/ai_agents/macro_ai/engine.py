"""Read-only Venus Macro AI orchestration."""

from __future__ import annotations

from .models import MacroAssessment, MarketSnapshot
from .scoring import assess_macro_bias


class VenusMacroAI:
    """Calculate deterministic XAUUSD macro confirmation."""

    def assess(
        self,
        snapshots: tuple[MarketSnapshot, ...],
    ) -> MacroAssessment:
        if not snapshots:
            raise ValueError("At least one market snapshot is required.")

        return assess_macro_bias(snapshots)
