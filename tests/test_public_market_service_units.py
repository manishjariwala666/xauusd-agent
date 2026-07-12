import inspect

from services import public_market_service


def test_live_market_signals_read_direct_table_without_cache() -> None:
    source = inspect.getsource(public_market_service.get_live_market_signals)

    assert "FROM public.market_signals" in source
    assert "ORDER BY signal_time DESC" in source
    assert "_crypto_cache" not in source
    assert "@st.cache" not in source
