"""Paid member Gold Signal feed contract tests."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_paid_dashboard_uses_canonical_market_signals() -> None:
    source = (ROOT / "user/dashboard.py").read_text()
    feed = source.split("def render_signal_feed", 1)[1].split("def _render_premium_access", 1)[0]
    assert 'supabase.table("market_signals")' in feed
    assert '.eq("symbol", "XAUUSD")' in feed
    assert '.eq("publication_status", "PUBLISHED")' in feed
    assert 'supabase.table("signals")' not in feed
    for protected_field in (
        "price", "stop_loss", "target_1", "target_2", "target_3",
        "target_4", "target_5", "target_6",
    ):
        assert protected_field in feed


def test_payment_gate_precedes_paid_signal_query() -> None:
    source = (ROOT / "user/dashboard.py").read_text()
    gate = "if not is_payment_verified() or payment_status != PAYMENT_VERIFIED:"
    call = 'render_signal_feed(supabase, "No published Gold Signal is available right now.")'
    assert gate in source
    assert call in source
    assert source.index(gate) < source.index(call)


def test_canonical_renderer_supports_six_targets() -> None:
    source = (ROOT / "user/dashboard.py").read_text()
    renderer = source.split("def _render_market_signal", 1)[1].split("def _render_signal", 1)[0]
    assert "for number in range(1, 7)" in renderer
    assert 'row.get(f"target_{number}")' in renderer
    assert 'side not in {"BUY", "SELL"}' in renderer
