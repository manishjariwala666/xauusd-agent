from datetime import date, datetime, timezone
from decimal import Decimal
import re
from types import SimpleNamespace

from services.ai_agents.economic_calendar.models import NewsLockDecision
from services.master_ai_signal_reader import MasterAISignalSnapshot
import services.captain_ai_runtime as runtime


def _snapshot(*, day_high=Decimal("4527.83"), day_low=Decimal("4484.10")):
    return MasterAISignalSnapshot(
        signal_date=date(2026, 8, 20),
        open_price=Decimal("4520"),
        high_price=Decimal("4527.83"),
        low_price=Decimal("4484.10"),
        close_price=Decimal("4490"),
        day_high=day_high,
        day_low=day_low,
        step=None,
        range_value=None,
        buy_base=Decimal("4493.37"),
        sell_base=Decimal("4522.78"),
        mode="Aggressive (0.25)",
        latest_slot="06:30 AM TO 07:30 AM",
        live_cmp=Decimal("4487.99"),
        buy_targets=(
            Decimal("4504.30"), Decimal("4515.23"), Decimal("4526.16"),
            Decimal("4537.09"), Decimal("4548.02"), Decimal("4558.95"),
        ),
        sell_targets=(
            Decimal("4511.85"), Decimal("4500.92"), Decimal("4489.99"),
            Decimal("4479.06"), Decimal("4468.13"), Decimal("4457.20"),
        ),
    )


class FakeSheets:
    _SESSION_HEADER = re.compile(r"^(?:XAUUSD SESSION\s+|DATE:\s*)(\d{4}-\d{2}-\d{2})$", re.I)
    _SLOT_LABEL = re.compile(
        r"^(\d{1,2}):(\d{2})(?:\s*(AM|PM))?\s*(?:-|TO)\s*"
        r"(\d{1,2}):(\d{2})(?:\s*(AM|PM))?$",
        re.I,
    )


def test_snapshot_as_of_excludes_later_opposite_base_sweep(monkeypatch):
    values = [
        ["DATE: 2026-08-20"],
        ["03:30 AM TO 04:30 AM", "4527.83", "4517.73", "", "4522.78", "4519.73"],
        ["04:30 AM TO 05:30 AM", "4525.76", "4511.27", "", "4518.52", "4512.40"],
        ["06:30 AM TO 07:30 AM", "4509.62", "4484.10", "", "4496.86", "4487.99"],
    ]
    monkeypatch.setattr(runtime, "GoogleSheetsService", FakeSheets)

    import services.sheet_signal_source as source

    monkeypatch.setattr(
        source,
        "_session_context_from_values",
        lambda *args, **kwargs: (
            Decimal("4527.83"),
            Decimal("4484.10"),
            Decimal("4493.37"),
            Decimal("4522.78"),
            _snapshot().buy_targets,
            _snapshot().sell_targets,
        ),
    )

    result = runtime._snapshot_as_of(
        _snapshot(),
        values,
        current_time=datetime(2026, 8, 19, 23, 0, tzinfo=timezone.utc),
        session_name="morning",
    )

    assert result.latest_slot == "03:30 AM TO 04:30 AM"
    assert result.day_high == Decimal("4527.83")
    assert result.day_low == Decimal("4517.73")
    assert result.day_low > result.buy_base
    assert result.day_high >= result.sell_base


def test_canonical_sell_candidate_uses_sell_base_entry_not_later_cmp(monkeypatch):
    current = _snapshot()
    history = tuple(
        MasterAISignalSnapshot(
            signal_date=date(2026, 8, 14 + index),
            open_price=Decimal("4400"),
            high_price=Decimal("4500"),
            low_price=Decimal("4300"),
            close_price=Decimal("4400"),
            day_high=Decimal("4500"),
            day_low=Decimal("4300"),
            step=None,
            range_value=None,
            buy_base=Decimal("4350"),
            sell_base=Decimal("4450"),
            mode="test",
            latest_slot="03:30 AM TO 04:30 AM",
            live_cmp=Decimal("4400"),
            buy_targets=(),
            sell_targets=(),
        )
        for index in range(4)
    )
    trigger_snapshot = _snapshot(day_low=Decimal("4517.73"))

    monkeypatch.setattr(
        runtime,
        "_load_current_history_values",
        lambda current_time: (current, history, [["DATE: 2026-08-20"]]),
    )
    monkeypatch.setattr(
        runtime,
        "_snapshot_as_of",
        lambda current, values, *, current_time, session_name=None: trigger_snapshot,
    )
    monkeypatch.setattr(
        runtime,
        "_news_and_macro",
        lambda current_time: (
            NewsLockDecision(False, "clear", None, None),
            SimpleNamespace(bias=SimpleNamespace(value="NEUTRAL"), confidence=0),
        ),
    )

    signal = SimpleNamespace(
        direction="SELL",
        reference_price=Decimal("4522.78"),
        stop_loss=Decimal("4527.83"),
        observed_at=datetime(2026, 8, 19, 23, 0, tzinfo=timezone.utc),
        external_key="gsheet-session:2026-08-20:morning:SELL",
        targets=trigger_snapshot.sell_targets,
    )

    observed = runtime.run_captain_sheet_candidate(signal)

    assert observed.live_cmp == Decimal("4522.78")
    assert observed.day_low == Decimal("4517.73")
    assert observed.assessment.decision.value == "APPROVE"
    assert observed.assessment.direction.value == "SELL"
