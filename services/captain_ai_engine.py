"""Deterministic read-only Captain AI gate for XAUUSD.

Captain never creates signals, writes databases, sends Telegram/WhatsApp,
or modifies Google Sheets. It only returns APPROVE / WAIT / REJECT.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from statistics import mean

from services.ai_agents.economic_calendar.models import NewsLockDecision
from services.master_ai_signal_reader import MasterAISignalSnapshot


class CaptainDecision(StrEnum):
    APPROVE = "APPROVE"
    WAIT = "WAIT"
    REJECT = "REJECT"


class CaptainDirection(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    NONE = "NONE"


@dataclass(frozen=True)
class FiveDayContext:
    trading_days: int
    weekly_high: Decimal
    weekly_low: Decimal
    weekly_range: Decimal
    average_daily_range: Decimal
    higher_highs: int
    lower_highs: int
    higher_lows: int
    lower_lows: int
    bias: str


@dataclass(frozen=True)
class CaptainAssessment:
    decision: CaptainDecision
    direction: CaptainDirection
    confidence: int
    weekly: FiveDayContext | None
    live_cmp: Decimal | None
    buy_base: Decimal | None
    sell_base: Decimal | None
    targets: tuple[Decimal, ...]
    stop_loss: Decimal | None
    news_locked: bool
    reasons: tuple[str, ...]
    macro_bias: str = "UNKNOWN"
    macro_confidence: int = 0
    read_only: bool = True
    signal_generated: bool = False
    delivery_started: bool = False


def build_five_day_context(
    snapshots: tuple[MasterAISignalSnapshot, ...],
) -> FiveDayContext | None:
    usable = [
        item
        for item in snapshots
        if item.high_price is not None
        and item.low_price is not None
        and item.high_price >= item.low_price
    ]

    if len(usable) < 4:
        return None

    usable = sorted(
        usable,
        key=lambda item: item.signal_date,
    )[-5:]

    highs = [item.high_price for item in usable]
    lows = [item.low_price for item in usable]

    assert all(value is not None for value in highs)
    assert all(value is not None for value in lows)

    high_values = [Decimal(value) for value in highs if value is not None]
    low_values = [Decimal(value) for value in lows if value is not None]

    ranges = [
        high - low
        for high, low in zip(high_values, low_values, strict=True)
    ]

    higher_highs = sum(
        current > previous
        for previous, current in zip(
            high_values,
            high_values[1:],
        )
    )
    lower_highs = sum(
        current < previous
        for previous, current in zip(
            high_values,
            high_values[1:],
        )
    )
    higher_lows = sum(
        current > previous
        for previous, current in zip(
            low_values,
            low_values[1:],
        )
    )
    lower_lows = sum(
        current < previous
        for previous, current in zip(
            low_values,
            low_values[1:],
        )
    )

    bullish_score = higher_highs + higher_lows
    bearish_score = lower_highs + lower_lows

    if bullish_score >= bearish_score + 2:
        bias = "BULLISH"
    elif bearish_score >= bullish_score + 2:
        bias = "BEARISH"
    else:
        bias = "MIXED"

    return FiveDayContext(
        trading_days=len(usable),
        weekly_high=max(high_values),
        weekly_low=min(low_values),
        weekly_range=max(high_values) - min(low_values),
        average_daily_range=Decimal(str(mean(ranges))),
        higher_highs=higher_highs,
        lower_highs=lower_highs,
        higher_lows=higher_lows,
        lower_lows=lower_lows,
        bias=bias,
    )


def assess_captain(
    *,
    current: MasterAISignalSnapshot,
    history: tuple[MasterAISignalSnapshot, ...],
    news_lock: NewsLockDecision | None = None,
    macro_bias: str = "UNKNOWN",
    macro_confidence: int = 0,
) -> CaptainAssessment:
    reasons: list[str] = []

    normalized_macro = str(macro_bias or "UNKNOWN").strip().upper()
    normalized_macro_confidence = max(
        0,
        min(100, int(macro_confidence or 0)),
    )

    weekly = build_five_day_context(history)

    if news_lock is not None and news_lock.locked:
        reasons.append(
            f"High-impact news lock active: {news_lock.reason}"
        )
        return CaptainAssessment(
            decision=CaptainDecision.WAIT,
            direction=CaptainDirection.NONE,
            confidence=100,
            weekly=weekly,
            live_cmp=current.live_cmp,
            buy_base=current.buy_base,
            sell_base=current.sell_base,
            targets=(),
            stop_loss=None,
            news_locked=True,
            macro_bias=normalized_macro,
            macro_confidence=normalized_macro_confidence,
            reasons=tuple(reasons),
        )

    if weekly is None:
        reasons.append(
            "At least four usable historical trading days are required."
        )
        return CaptainAssessment(
            decision=CaptainDecision.WAIT,
            direction=CaptainDirection.NONE,
            confidence=0,
            weekly=None,
            live_cmp=current.live_cmp,
            buy_base=current.buy_base,
            sell_base=current.sell_base,
            targets=(),
            stop_loss=None,
            news_locked=False,
            macro_bias=normalized_macro,
            macro_confidence=normalized_macro_confidence,
            reasons=tuple(reasons),
        )

    cmp_price = current.live_cmp
    buy_base = current.buy_base
    sell_base = current.sell_base

    if cmp_price is None or buy_base is None or sell_base is None:
        reasons.append(
            "Current CMP or session Buy/Sell Base is unavailable."
        )
        return CaptainAssessment(
            decision=CaptainDecision.REJECT,
            direction=CaptainDirection.NONE,
            confidence=0,
            weekly=weekly,
            live_cmp=cmp_price,
            buy_base=buy_base,
            sell_base=sell_base,
            targets=(),
            stop_loss=None,
            news_locked=False,
            macro_bias=normalized_macro,
            macro_confidence=normalized_macro_confidence,
            reasons=tuple(reasons),
        )

    if buy_base >= sell_base:
        reasons.append("Session Buy Base must be below Sell Base.")
        return CaptainAssessment(
            decision=CaptainDecision.REJECT,
            direction=CaptainDirection.NONE,
            confidence=0,
            weekly=weekly,
            live_cmp=cmp_price,
            buy_base=buy_base,
            sell_base=sell_base,
            targets=(),
            stop_loss=None,
            news_locked=False,
            macro_bias=normalized_macro,
            macro_confidence=normalized_macro_confidence,
            reasons=tuple(reasons),
        )

    # Critical protection against the old "entry in the middle" behaviour.
    if buy_base < cmp_price < sell_base:
        reasons.append(
            "CMP is between Buy Base and Sell Base; mid-range entry blocked."
        )
        return CaptainAssessment(
            decision=CaptainDecision.WAIT,
            direction=CaptainDirection.NONE,
            confidence=90,
            weekly=weekly,
            live_cmp=cmp_price,
            buy_base=buy_base,
            sell_base=sell_base,
            targets=(),
            stop_loss=None,
            news_locked=False,
            macro_bias=normalized_macro,
            macro_confidence=normalized_macro_confidence,
            reasons=tuple(reasons),
        )

    if cmp_price <= buy_base:
        direction = CaptainDirection.BUY
        targets = current.buy_targets

        if len(targets) != 6:
            reasons.append(
                "Official BUY Target 1-6 are not all available."
            )
            return CaptainAssessment(
                decision=CaptainDecision.REJECT,
                direction=direction,
                confidence=0,
                weekly=weekly,
                live_cmp=cmp_price,
                buy_base=buy_base,
                sell_base=sell_base,
                targets=targets,
                stop_loss=None,
                news_locked=False,
                macro_bias=normalized_macro,
                macro_confidence=normalized_macro_confidence,
                reasons=tuple(reasons),
            )

        if (
            targets[0] <= buy_base
            or any(
                current_target <= previous_target
                for previous_target, current_target in zip(
                    targets,
                    targets[1:],
                )
            )
        ):
            reasons.append(
                "Official BUY targets must be above Buy Base "
                "and strictly increase from T1 through T6."
            )
            return CaptainAssessment(
                decision=CaptainDecision.REJECT,
                direction=direction,
                confidence=0,
                weekly=weekly,
                live_cmp=cmp_price,
                buy_base=buy_base,
                sell_base=sell_base,
                targets=targets,
                stop_loss=None,
                news_locked=False,
                macro_bias=normalized_macro,
                macro_confidence=normalized_macro_confidence,
                reasons=tuple(reasons),
            )

        if any(target <= cmp_price for target in targets):
            reasons.append(
                "BUY targets must remain above the proposed entry."
            )
            return CaptainAssessment(
                decision=CaptainDecision.REJECT,
                direction=direction,
                confidence=0,
                weekly=weekly,
                live_cmp=cmp_price,
                buy_base=buy_base,
                sell_base=sell_base,
                targets=targets,
                stop_loss=None,
                news_locked=False,
                macro_bias=normalized_macro,
                macro_confidence=normalized_macro_confidence,
                reasons=tuple(reasons),
            )

        if weekly.bias == "BEARISH":
            reasons.append(
                "Five-day structure is bearish; BUY requires confirmation."
            )
            return CaptainAssessment(
                decision=CaptainDecision.WAIT,
                direction=direction,
                confidence=65,
                weekly=weekly,
                live_cmp=cmp_price,
                buy_base=buy_base,
                sell_base=sell_base,
                targets=targets,
                stop_loss=None,
                news_locked=False,
                macro_bias=normalized_macro,
                macro_confidence=normalized_macro_confidence,
                reasons=tuple(reasons),
            )

        stop_loss = current.day_low

        if stop_loss is None or stop_loss >= cmp_price:
            reasons.append(
                "BUY stop loss must be the active-session low below entry."
            )
            return CaptainAssessment(
                decision=CaptainDecision.REJECT,
                direction=direction,
                confidence=0,
                weekly=weekly,
                live_cmp=cmp_price,
                buy_base=buy_base,
                sell_base=sell_base,
                targets=targets,
                stop_loss=stop_loss,
                news_locked=False,
                macro_bias=normalized_macro,
                macro_confidence=normalized_macro_confidence,
                reasons=tuple(reasons),
            )

        reasons.append(
            "BUY location is at/below Buy Base with valid Target 1-6 "
            "and active-session low stop loss."
        )

    else:
        direction = CaptainDirection.SELL
        targets = current.sell_targets

        if len(targets) != 6:
            reasons.append(
                "Official SELL Target 1-6 are not all available."
            )
            return CaptainAssessment(
                decision=CaptainDecision.REJECT,
                direction=direction,
                confidence=0,
                weekly=weekly,
                live_cmp=cmp_price,
                buy_base=buy_base,
                sell_base=sell_base,
                targets=targets,
                stop_loss=None,
                news_locked=False,
                macro_bias=normalized_macro,
                macro_confidence=normalized_macro_confidence,
                reasons=tuple(reasons),
            )

        if (
            targets[0] >= sell_base
            or any(
                current_target >= previous_target
                for previous_target, current_target in zip(
                    targets,
                    targets[1:],
                )
            )
        ):
            reasons.append(
                "Official SELL targets must be below Sell Base "
                "and strictly decrease from T1 through T6."
            )
            return CaptainAssessment(
                decision=CaptainDecision.REJECT,
                direction=direction,
                confidence=0,
                weekly=weekly,
                live_cmp=cmp_price,
                buy_base=buy_base,
                sell_base=sell_base,
                targets=targets,
                stop_loss=None,
                news_locked=False,
                macro_bias=normalized_macro,
                macro_confidence=normalized_macro_confidence,
                reasons=tuple(reasons),
            )

        if any(target >= cmp_price for target in targets):
            reasons.append(
                "SELL targets must remain below the proposed entry."
            )
            return CaptainAssessment(
                decision=CaptainDecision.REJECT,
                direction=direction,
                confidence=0,
                weekly=weekly,
                live_cmp=cmp_price,
                buy_base=buy_base,
                sell_base=sell_base,
                targets=targets,
                stop_loss=None,
                news_locked=False,
                macro_bias=normalized_macro,
                macro_confidence=normalized_macro_confidence,
                reasons=tuple(reasons),
            )

        if weekly.bias == "BULLISH":
            reasons.append(
                "Five-day structure is bullish; SELL requires confirmation."
            )
            return CaptainAssessment(
                decision=CaptainDecision.WAIT,
                direction=direction,
                confidence=65,
                weekly=weekly,
                live_cmp=cmp_price,
                buy_base=buy_base,
                sell_base=sell_base,
                targets=targets,
                stop_loss=None,
                news_locked=False,
                macro_bias=normalized_macro,
                macro_confidence=normalized_macro_confidence,
                reasons=tuple(reasons),
            )

        stop_loss = current.day_high

        if stop_loss is None or stop_loss <= cmp_price:
            reasons.append(
                "SELL stop loss must be the active-session high above entry."
            )
            return CaptainAssessment(
                decision=CaptainDecision.REJECT,
                direction=direction,
                confidence=0,
                weekly=weekly,
                live_cmp=cmp_price,
                buy_base=buy_base,
                sell_base=sell_base,
                targets=targets,
                stop_loss=stop_loss,
                news_locked=False,
                macro_bias=normalized_macro,
                macro_confidence=normalized_macro_confidence,
                reasons=tuple(reasons),
            )

        reasons.append(
            "SELL location is at/above Sell Base with valid Target 1-6 "
            "and active-session high stop loss."
        )

    confidence = 85 if weekly.bias != "MIXED" else 72

    if (
        direction is CaptainDirection.BUY
        and normalized_macro == "BULLISH_GOLD"
    ):
        boost = min(
            10,
            normalized_macro_confidence // 10,
        )
        confidence = min(95, confidence + boost)
        reasons.append(
            "Macro-news bias supports BUY."
        )

    elif (
        direction is CaptainDirection.SELL
        and normalized_macro == "BEARISH_GOLD"
    ):
        boost = min(
            10,
            normalized_macro_confidence // 10,
        )
        confidence = min(95, confidence + boost)
        reasons.append(
            "Macro-news bias supports SELL."
        )

    elif (
        (
            direction is CaptainDirection.BUY
            and normalized_macro == "BEARISH_GOLD"
        )
        or
        (
            direction is CaptainDirection.SELL
            and normalized_macro == "BULLISH_GOLD"
        )
    ):
        confidence = max(0, confidence - 20)
        reasons.append(
            "Macro-news bias conflicts with technical direction."
        )

    return CaptainAssessment(
        decision=CaptainDecision.APPROVE,
        direction=direction,
        confidence=confidence,
        weekly=weekly,
        live_cmp=cmp_price,
        buy_base=buy_base,
        sell_base=sell_base,
        targets=targets,
        stop_loss=stop_loss,
        news_locked=False,
        macro_bias=normalized_macro,
        macro_confidence=normalized_macro_confidence,
        reasons=tuple(reasons),
    )
