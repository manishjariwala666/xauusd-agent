"""Captain verification gate for candidate signal delivery."""
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

def shadow_verification_enabled() -> bool:
    return os.getenv("CAPTAIN_SIGNAL_SHADOW_GATE", "").strip().lower() in {"1", "true", "yes", "on"}

def shadow_gate_enabled() -> bool:
    """Legacy blanket blocker is disabled; verification happens per signal."""
    return False

def evaluate_signal_shadow_gate(signal: dict[str, Any], *, runner: Callable[..., Any] = run_captain_read_only) -> CaptainShadowGateResult:
    if not shadow_verification_enabled():
        return CaptainShadowGateResult(False, False, "NOT_RUN", "NONE", 0, "UNKNOWN", 0, False, "Captain verification disabled.")
    try:
        assessment = runner()
    except Exception:
        return CaptainShadowGateResult(True, True, "ERROR", "NONE", 0, "UNKNOWN", 0, True, "Captain assessment failed; delivery blocked.")
    decision = str(assessment.decision.value)
    direction = str(assessment.direction.value)
    candidate = str(signal.get("signal_type") or "").strip().upper()
    reasons = tuple(str(item) for item in getattr(assessment, "reasons", ()))
    blocked = decision != "APPROVE" or direction != candidate
    if decision != "APPROVE":
        reason = reasons[0] if reasons else f"Captain decision is {decision}."
    elif direction != candidate:
        reason = f"Captain direction mismatch: captain={direction}, candidate={candidate or 'NONE'}."
    else:
        reason = reasons[0] if reasons else "Captain verified candidate delivery."
    # Telegram's existing sender checks enabled; keep it synonymous with blocked.
    return CaptainShadowGateResult(blocked, blocked, decision, direction, int(assessment.confidence), str(assessment.macro_bias), int(assessment.macro_confidence), bool(assessment.news_locked), reason)
