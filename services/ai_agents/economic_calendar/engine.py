"""Deterministic read-only economic event assessment."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from .models import (
    EconomicEvent,
    EventAssessment,
    EventBias,
    EventImpact,
    NewsLockDecision,
)
from .registry import EVENT_RULES


class EconomicCalendarAI:
    def should_lock_signals(
        self,
        events: tuple[EconomicEvent, ...],
        *,
        now: datetime | None = None,
        pre_lock_minutes: int = 15,
        post_lock_minutes: int = 10,
    ) -> NewsLockDecision:
        current = now or datetime.now(timezone.utc)

        for event in sorted(events, key=lambda item: item.scheduled_at):
            if event.impact is not EventImpact.HIGH:
                continue

            delta = int((event.scheduled_at - current).total_seconds())

            if -post_lock_minutes * 60 <= delta <= pre_lock_minutes * 60:
                return NewsLockDecision(
                    locked=True,
                    reason=f"{event.country.value} high-impact event window",
                    event_id=event.event_id,
                    seconds_to_event=delta,
                )

        return NewsLockDecision(
            locked=False,
            reason="No high-impact event inside lock window",
            event_id=None,
            seconds_to_event=None,
        )

    def assess_event(self, event: EconomicEvent) -> EventAssessment:
        if event.actual is None or event.forecast is None:
            return EventAssessment(
                event_id=event.event_id,
                bias=EventBias.UNKNOWN,
                surprise=None,
                confidence=0,
                rationale=("Actual or forecast value missing.",),
            )

        title = " ".join(event.title.lower().split())
        rule = next(
            (
                item
                for item in EVENT_RULES
                if item.country is event.country
                and item.key in title
            ),
            None,
        )

        if rule is None:
            return EventAssessment(
                event_id=event.event_id,
                bias=EventBias.UNKNOWN,
                surprise=None,
                confidence=0,
                rationale=("No approved event rule matched.",),
            )

        surprise = event.actual - event.forecast

        if surprise == Decimal("0"):
            return EventAssessment(
                event_id=event.event_id,
                bias=EventBias.NEUTRAL,
                surprise=surprise,
                confidence=40,
                rationale=("Actual matched forecast.",),
            )

        stronger_usd = (
            surprise > 0
            if rule.stronger_actual_supports_usd
            else surprise < 0
        )

        bias = (
            EventBias.BEARISH_GOLD
            if stronger_usd
            else EventBias.BULLISH_GOLD
        )

        confidence = min(
            95,
            55 + int(min(abs(surprise), Decimal("40"))),
        )

        return EventAssessment(
            event_id=event.event_id,
            bias=bias,
            surprise=surprise,
            confidence=confidence,
            rationale=(
                f"Actual={event.actual}",
                f"Forecast={event.forecast}",
                f"Surprise={surprise}",
                (
                    "USD-supportive surprise."
                    if stronger_usd
                    else "USD-negative surprise."
                ),
            ),
        )
