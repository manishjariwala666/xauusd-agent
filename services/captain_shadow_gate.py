"""Read-only Captain shadow gate for candidate signal delivery.

When explicitly enabled, this gate evaluates Captain AI and blocks
external delivery regardless of APPROVE/WAIT/REJECT.

It performs no signal generation, database mutation, Telegram send,
or WhatsApp send.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable

from services.captain_ai_runtime import run_captain_read_only


@dataclass(frozen=True)
class CaptainShadowGateResult:
    enabled: bool
    blocked: bool
    decision: str
    direction: str
    confidence: int
    macro_bias: str
    macro_confidence: int
    news_locked: bool
    reason: str


def shadow_gate_enabled() -> bool:
    return os.getenv(
        "CAPTAIN_SIGNAL_SHADOW_GATE",
        "",
    ).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def evaluate_signal_shadow_gate(
    signal: dict[str, Any],
    *,
    runner: Callable[..., Any] = run_captain_read_only,
) -> CaptainShadowGateResult:
    if not shadow_gate_enabled():
        return CaptainShadowGateResult(
            enabled=False,
            blocked=False,
            decision="NOT_RUN",
            direction="NONE",
            confidence=0,
            macro_bias="UNKNOWN",
            macro_confidence=0,
            news_locked=False,
            reason="Captain shadow gate disabled.",
        )

    try:
        assessment = runner()
    except Exception:
        # Shadow mode must fail closed.
        return CaptainShadowGateResult(
            enabled=True,
            blocked=True,
            decision="ERROR",
            direction="NONE",
            confidence=0,
            macro_bias="UNKNOWN",
            macro_confidence=0,
            news_locked=True,
            reason="Captain shadow assessment failed; delivery blocked.",
        )

    reasons = tuple(
        str(item)
        for item in getattr(assessment, "reasons", ())
    )

    return CaptainShadowGateResult(
        enabled=True,
        blocked=True,
        decision=str(assessment.decision.value),
        direction=str(assessment.direction.value),
        confidence=int(assessment.confidence),
        macro_bias=str(assessment.macro_bias),
        macro_confidence=int(assessment.macro_confidence),
        news_locked=bool(assessment.news_locked),
        reason=(
            reasons[0]
            if reasons
            else "Captain shadow assessment completed."
        ),
    )
