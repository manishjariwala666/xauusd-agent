from datetime import datetime, timezone
from decimal import Decimal
import re
from types import SimpleNamespace

import services.sheet_signal_source as signal_source
from services.sheet_signal_source import load_authoritative_sheet_signal


class FakeSheets:
    _SESSION_HEADER = re.compile(
        r"^(?:XAUUSD SESSION\s+|DATE:\s*)(\d{4}-\d{2}-\d{2})$",
        re.IGNORECASE,
    )
    _SLOT_LABEL = re.compile(
        r"^(\d{1,2}):(\d{2})(?:\s*(AM|PM))?\s*"
        r"(?:-|TO)\s*(\d{1,2}):(\d{2})(?:\s*(AM|PM))?$",
        re.IGNORECASE,
    )
    _ANALYSIS_WORKSHEET = "Sheet1"
    _MAX_ANALYSIS_AGE = None

    def __init__(self, values):
        self.values = values
        self.parse_calls = 0
        self.legacy_calls = 0

    def _analysis_values(self):
        return self.values

    def parse_latest_analysis_signal(self, values, *, now, max_age):
        self.parse_calls += 1
        return None

    def get_latest_signal(self):
        self.legacy_calls += 1
        return None

    def _select_analysis_targets(
        self,
        *,
        direction,
        entry_price,
        raw_targets,
        fallback_high,
        fallback_low,
    ):
        del fallback_high, fallback_low
        directional = [
            value
            for value in raw_targets
            if (
                (direction == "BUY" and value > entry_price)
                or (direction == "SELL" and value < entry_price)
            )
        ]
        if not directional:
            return None
        targets = tuple(directional)
        return targets[0], targets, targets


def _hourly_row(
    slot,
    high,
    low,
    cmp,
    *,
    buy_target="",
    sell_target="",
    session="",
):
    row = [slot, high, low, "", "", cmp, "", "", buy_target, sell_target]
    row.extend(["", "", "", session])
    return row


def test_missed_morning_sell_is_recovered_after_sheet_advances_to_evening(monkeypatch):
    values = [
        ["DATE: 2026-08-20"],
        ["MORNING SESSION", "Session High", "Session Low", "Buy Base", "Sell Base", "Mode"],
        ["", "4527.83", "4484.10", "4493.37", "4522.78", "Aggressive"],
        ["EVENING SESSION", "Session High", "Session Low", "Buy Base", "Sell Base", "Mode"],
        ["", "4510.00", "4470.00", "4485.00", "4505.00", "Aggressive"],
        ["Time", "High", "Low", "Prev AVG", "AVG", "LIVE CMP"],
        _hourly_row(
            "03:30 AM TO 04:30 AM",
            "4527.83",
            "4517.73",
            "4519.73",
            buy_target="4504.30",
            sell_target="4511.85",
            session="MORNING SESSION",
        ),
        _hourly_row(
            "04:30 AM TO 05:30 AM",
            "4520.00",
            "4510.00",
            "4512.00",
            buy_target="4515.23",
            sell_target="4500.92",
            session="MORNING SESSION",
        ),
        # Opposite Buy Base is swept later in the morning; it must not erase
        # the earlier valid one-sided SELL trigger when the scheduler catches up.
        _hourly_row(
            "06:30 AM TO 07:30 AM",
            "4500.00",
            "4484.10",
            "4495.00",
            buy_target="4526.16",
            sell_target="4489.99",
            session="MORNING SESSION",
        ),
        _hourly_row(
            "02:30 PM TO 03:30 PM",
            "4508.00",
            "4498.00",
            "4502.00",
            buy_target="4518.00",
            sell_target="4492.00",
            session="EVENING SESSION",
        ),
    ]
    snapshot = SimpleNamespace(
        latest_slot="02:30 PM TO 03:30 PM",
        day_high=Decimal("4510.00"),
        day_low=Decimal("4470.00"),
        buy_base=Decimal("4485.00"),
        sell_base=Decimal("4505.00"),
        buy_targets=(Decimal("4518.00"),),
        sell_targets=(Decimal("4492.00"),),
    )
    monkeypatch.setattr(
        signal_source,
        "parse_signal_snapshot",
        lambda values, *, target_date: snapshot,
    )
    sheets = FakeSheets(values)

    result = load_authoritative_sheet_signal(
        sheets,
        # 11:00 UTC = 16:30 IST: Evening session has already started.
        now=datetime(2026, 8, 20, 11, 0, tzinfo=timezone.utc),
    )

    assert result is not None
    assert result.direction == "SELL"
    assert result.reference_price == Decimal("4522.78")
    assert result.stop_loss == Decimal("4527.83")
    assert result.targets[:3] == (
        Decimal("4511.85"),
        Decimal("4500.92"),
        Decimal("4489.99"),
    )
    assert result.external_key == "gsheet-session:2026-08-20:morning:SELL"
    assert result.observed_at == datetime(2026, 8, 19, 23, 0, tzinfo=timezone.utc)
    assert "MORNING SESSION" in result.label
    assert sheets.parse_calls == 0
    assert sheets.legacy_calls == 0
