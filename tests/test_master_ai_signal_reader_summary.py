from datetime import date
from decimal import Decimal

from services.master_ai_signal_reader import parse_signal_snapshot


def test_summary_columns_are_mapped_by_header_name() -> None:
    values = [
        ["DATE: 2026-08-06"],
        [
            "Open",
            "High",
            "Low",
            "Close",
            "",
            "",
            "",
            "MORNING SESSION",
            "Session Time",
            "Session High",
            "Session Low",
            "Buy Base",
            "Sell Base",
            "Mode",
        ],
        [
            "4249.46",
            "4304.07",
            "4244.13",
            "4268.58",
            "",
            "",
            "",
            "READY",
            "03:30 AM - 02:30 PM",
            "4304.07",
            "4244.13",
            "4250.00",
            "4289.52",
            "Aggressive (0.25)",
        ],
        [
            "Time",
            "High",
            "Low",
            "Prev AVG",
            "AVG",
            "LIVE CMP",
        ],
        [
            "01:30 PM TO 02:30 PM",
            "4268.58",
            "4268.58",
            "4258.32",
            "4268.58",
            "4268.58",
        ],
    ]

    snapshot = parse_signal_snapshot(
        values,
        target_date=date(2026, 8, 6),
    )

    assert snapshot is not None
    assert snapshot.open_price == Decimal("4249.46")
    assert snapshot.high_price == Decimal("4304.07")
    assert snapshot.low_price == Decimal("4244.13")
    assert snapshot.close_price == Decimal("4268.58")
    assert snapshot.day_high == Decimal("4304.07")
    assert snapshot.day_low == Decimal("4244.13")
    assert snapshot.live_cmp == Decimal("4268.58")
    assert snapshot.latest_slot == "01:30 PM TO 02:30 PM"
    assert snapshot.buy_base == Decimal("4250.00")
    assert snapshot.sell_base == Decimal("4289.52")
    assert snapshot.mode == "Aggressive (0.25)"
    assert snapshot.step is None
    assert snapshot.range_value is None
