from datetime import datetime, timedelta, timezone
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
    _MAX_ANALYSIS_AGE = timedelta(hours=6)

    def __init__(self, values, parsed):
        self.values = values
        self.parsed = parsed
        self.legacy_calls = 0
        self.parse_calls = 0

    def _analysis_values(self):
        return self.values

    def parse_latest_analysis_signal(self, values, *, now, max_age):
        assert values is self.values
        assert max_age == self._MAX_ANALYSIS_AGE
        self.parse_calls += 1
        return self.parsed

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
        slots = tuple(directional)
        return directional[0], tuple(directional), slots

    def get_latest_signal(self):
        self.legacy_calls += 1
        return SimpleNamespace(
            direction="SELL",
            target_price=Decimal("4300"),
            stop_loss=Decimal("4500"),
            external_key="legacy-stale",
        )


def test_canonical_session_overrides_stale_legacy_sl_tp():
    canonical = SimpleNamespace(
        direction="BUY",
        reference_price=Decimal("4332.95"),
        target_price=Decimal("4350.00"),
        targets=(Decimal("4350.00"), Decimal("4360.00")),
        stop_loss=Decimal("4318.00"),
        external_key="gsheet-session:2026-08-19:morning:BUY",
    )
    sheets = FakeSheets(
        [["DATE: 2026-08-19"], ["canonical data"]],
        canonical,
    )

    result = load_authoritative_sheet_signal(
        sheets,
        now=datetime(2026, 8, 19, 9, 0, tzinfo=timezone.utc),
    )

    assert result is canonical
    assert result.target_price == Decimal("4350.00")
    assert result.stop_loss == Decimal("4318.00")
    assert sheets.parse_calls == 1
    assert sheets.legacy_calls == 0


def test_canonical_session_without_fresh_signal_fails_closed():
    sheets = FakeSheets(
        [["XAUUSD SESSION 2026-08-19"], ["stale or invalid"]],
        None,
    )

    result = load_authoritative_sheet_signal(
        sheets,
        now=datetime(2026, 8, 19, 9, 0, tzinfo=timezone.utc),
    )

    assert result is None
    assert sheets.parse_calls == 1
    assert sheets.legacy_calls == 0


def test_legacy_source_remains_fallback_only_without_canonical_sessions():
    sheets = FakeSheets([["plain structured worksheet"]], None)

    result = load_authoritative_sheet_signal(
        sheets,
        now=datetime(2026, 8, 19, 9, 0, tzinfo=timezone.utc),
    )

    assert result.external_key == "legacy-stale"
    assert sheets.parse_calls == 0
    assert sheets.legacy_calls == 1


def test_first_closed_bar_sell_base_cross_is_not_skipped(monkeypatch):
    values = [
        ["DATE: 2026-08-20"],
        ["Time", "High", "Low", "Prev AVG", "AVG", "LIVE CMP"],
        [
            "03:30 AM TO 04:30 AM",
            "4527.83",
            "4517.73",
            "",
            "4522.78",
            "4519.73",
        ],
    ]
    snapshot = SimpleNamespace(
        latest_slot="03:30 AM TO 04:30 AM",
        buy_base=Decimal("4493.37"),
        sell_base=Decimal("4522.78"),
        day_high=Decimal("4527.83"),
        day_low=Decimal("4484.10"),
        buy_targets=(
            Decimal("4504.30"),
            Decimal("4515.23"),
            Decimal("4526.16"),
        ),
        sell_targets=(
            Decimal("4511.85"),
            Decimal("4500.92"),
            Decimal("4489.99"),
            Decimal("4479.06"),
            Decimal("4468.13"),
            Decimal("4457.20"),
        ),
    )
    monkeypatch.setattr(
        signal_source,
        "parse_signal_snapshot",
        lambda values, *, target_date: snapshot,
    )
    sheets = FakeSheets(values, None)

    result = load_authoritative_sheet_signal(
        sheets,
        # 05:00 UTC = 10:30 IST, safely after the first bar close.
        now=datetime(2026, 8, 20, 5, 0, tzinfo=timezone.utc),
    )

    assert result is not None
    assert result.direction == "SELL"
    assert result.reference_price == Decimal("4522.78")
    assert result.target_price == Decimal("4511.85")
    assert result.targets[:3] == (
        Decimal("4511.85"),
        Decimal("4500.92"),
        Decimal("4489.99"),
    )
    assert result.stop_loss == Decimal("4527.83")
    assert result.external_key == "gsheet-session:2026-08-20:morning:SELL"
    assert "SELL Base closed-bar trigger" in result.label
    assert sheets.parse_calls == 0
    assert sheets.legacy_calls == 0
