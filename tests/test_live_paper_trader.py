from datetime import datetime, timezone
from decimal import Decimal

from services.live_paper_trader import (
    DataUnavailableError,
    PaperTrader,
    SheetParameters,
    UnauthorizedError,
)


def row(**extra):
    value = {
        "i_useAggressive": "true",
        "valBuyLevel": "2300",
        "valSellLevel": "2400",
        "lvlT1": "2310",
        "lvlT2": "2320",
        "lvlS1": "2390",
        "lvlS2": "2380",
    }
    value.update(extra)
    return value


class Sheet:
    def __init__(self, values=None): self.values = values or row()
    def latest(self): return SheetParameters.from_row(self.values)


class Price:
    def __init__(self, values): self.values = iter(values)
    def latest(self): return next(self.values)


class Notify:
    def __init__(self): self.messages = []
    def notify(self, title, message): self.messages.append((title, message))


def quote(value): return Decimal(str(value)), datetime(2026, 9, 18, tzinfo=timezone.utc), "test"


def test_sheet_parameters_parse_required_levels():
    params = SheetParameters.from_row(row())
    assert params.aggressive is True
    assert params.buy_base == Decimal("2300")
    assert params.sell_base == Decimal("2400")
    assert params.buy_targets == (Decimal("2310"), Decimal("2320"))
    assert params.sell_targets == (Decimal("2390"), Decimal("2380"))


def test_buy_open_and_target_notification():
    notify = Notify()
    trader = PaperTrader(Sheet(), Price([quote("2299"), quote("2310")]), notify)
    assert "PAPER OPEN BUY" in trader.tick()
    assert "PAPER TARGET BUY T1" in trader.tick()
    assert len(notify.messages) == 2


def test_sell_open_and_stop():
    trader = PaperTrader(Sheet(row(valSellStop="2405")), Price([quote("2401"), quote("2410")]))
    assert "PAPER OPEN SELL" in trader.tick()
    assert "PAPER STOP SELL" in trader.tick()
    assert trader.position is None


def test_unauthorized_provider_never_opens_position():
    class BadPrice:
        def latest(self): raise UnauthorizedError("401")
    trader = PaperTrader(Sheet(), BadPrice())
    assert "BLOCK unauthorized" in trader.tick()
    assert trader.position is None


def test_missing_data_is_recoverable():
    class MissingSheet:
        def latest(self): raise DataUnavailableError("missing")
    trader = PaperTrader(MissingSheet(), Price([]))
    assert "WAIT data unavailable" in trader.tick()


def test_live_price_401_is_a_hard_authorization_block(monkeypatch):
    from services.live_paper_trader import LiveXauUsdPriceSource

    class Response:
        status_code = 401

    monkeypatch.setattr("services.live_paper_trader.requests.get", lambda *args, **kwargs: Response())
    trader = PaperTrader(Sheet(), LiveXauUsdPriceSource(goldapi_key="bad"))
    assert "BLOCK unauthorized" in trader.tick()
    assert trader.position is None
