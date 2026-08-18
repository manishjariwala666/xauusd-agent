"""Captain verification gate for candidate signal delivery."""
from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Any, Callable
from loguru import logger
from services.captain_ai_runtime import CaptainObservedRun, run_captain_observed
from services.captain_shadow_audit import record_captain_shadow_audit


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
    observed: CaptainObservedRun | None = None
    audit_correlation_id: str | None = None
    audit_persisted: bool | None = None
    master_ai_summary: str | None = None


def shadow_verification_enabled() -> bool:
    return os.getenv("CAPTAIN_SIGNAL_SHADOW_GATE", "").strip().lower() in {"1", "true", "yes", "on"}


def shadow_gate_enabled() -> bool:
    """Legacy blanket blocker is disabled; verification happens per signal."""
    return False


def _assessment_and_observed(value: Any) -> tuple[Any, CaptainObservedRun | None]:
    """Accept both the new observed runtime and legacy assessment test doubles."""
    if isinstance(value, CaptainObservedRun):
        return value.assessment, value
    assessment = getattr(value, "assessment", None)
    if assessment is not None and hasattr(value, "signal_date"):
        return assessment, value
    return value, None


def _audit_gate_decision(
    observed: CaptainObservedRun | None,
    *,
    signal: dict[str, Any],
    blocked: bool,
    reason: str,
) -> tuple[str | None, bool | None, str | None]:
    """Persist observability only; never alter the delivery decision."""
    if observed is None:
        return None, None, None
    try:
        signal_id = signal.get("id")
        audit = record_captain_shadow_audit(
            observed,
            source_interface="SIGNAL_AGENT",
            shadow_status="BLOCKED" if blocked else "VERIFIED",
            shadow_reason=reason,
            signal_id=int(signal_id) if signal_id is not None else None,
        )
        return audit.correlation_id, audit.persisted, audit.master_ai_summary
    except Exception as exc:
        logger.warning(
            "Captain/Shadow delivery audit failed without changing gate decision: type={}",
            type(exc).__name__,
        )
        return None, False, None


def evaluate_signal_shadow_gate(
    signal: dict[str, Any],
    *,
    runner: Callable[..., Any] = run_captain_observed,
) -> CaptainShadowGateResult:
    if not shadow_verification_enabled():
        return CaptainShadowGateResult(
            False, False, "NOT_RUN", "NONE", 0, "UNKNOWN", 0, False,
            "Captain verification disabled.", None, None, None, None,
        )
    try:
        raw = runner()
        assessment, observed = _assessment_and_observed(raw)
    except Exception:
        return CaptainShadowGateResult(
            True, True, "ERROR", "NONE", 0, "UNKNOWN", 0, True,
            "Captain assessment failed; delivery blocked.", None, None, False, None,
        )

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

    correlation_id, audit_persisted, master_ai_summary = _audit_gate_decision(
        observed,
        signal=signal,
        blocked=blocked,
        reason=reason,
    )

    return CaptainShadowGateResult(
        blocked,
        blocked,
        decision,
        direction,
        int(assessment.confidence),
        str(assessment.macro_bias),
        int(assessment.macro_confidence),
        bool(assessment.news_locked),
        reason,
        observed,
        correlation_id,
        audit_persisted,
        master_ai_summary,
    )
