"""Fail-closed Google Sheet driven XAUUSD paper-trading monitor.

The monitor never places a broker order.  It only emits paper position state
changes after a fresh Sheet snapshot and a live quote are available.  A 401
from either provider stops that cycle and cannot create a trade.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import os
import shutil
import subprocess
from time import monotonic, sleep
from typing import Any, Callable, Mapping, Protocol

import requests
import yfinance as yf
from loguru import logger

from services.google_sheets_service import PrivateGoogleSheetsService


class UnauthorizedError(RuntimeError):
    """Provider authentication failed; trading must remain disabled."""


class DataUnavailableError(RuntimeError):
    """A provider returned no usable data."""


def _decimal(value: Any, name: str) -> Decimal:
    try:
        parsed = Decimal(str(value).strip().replace(",", ""))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise DataUnavailableError(f"Missing or invalid Sheet value: {name}") from exc
    if not parsed.is_finite():
        raise DataUnavailableError(f"Missing or invalid Sheet value: {name}")
    return parsed


def _optional_decimal(row: Mapping[str, Any], *names: str) -> Decimal | None:
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return _decimal(value, name)
    return None


def _bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class SheetParameters:
    aggressive: bool
    buy_base: Decimal
    sell_base: Decimal
    buy_targets: tuple[Decimal, ...]
    sell_targets: tuple[Decimal, ...]
    buy_stop: Decimal | None = None
    sell_stop: Decimal | None = None
    row_timestamp: str = ""

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "SheetParameters":
        normalized = {str(k).strip(): v for k, v in row.items()}
        buy_targets = tuple(
            _decimal(normalized[key], key)
            for key in ("lvlT1", "lvlT2", "lvlT3", "lvlT4", "lvlT5", "lvlT6")
            if normalized.get(key) not in (None, "")
        )
        sell_targets = tuple(
            _decimal(normalized[key], key)
            for key in ("lvlS1", "lvlS2", "lvlS3", "lvlS4", "lvlS5", "lvlS6")
            if normalized.get(key) not in (None, "")
        )
        if not buy_targets and not sell_targets:
            raise DataUnavailableError("Sheet row contains no target levels.")
        return cls(
            aggressive=_bool(normalized.get("i_useAggressive")),
            buy_base=_decimal(normalized.get("valBuyLevel"), "valBuyLevel"),
            sell_base=_decimal(normalized.get("valSellLevel"), "valSellLevel"),
            buy_targets=buy_targets,
            sell_targets=sell_targets,
            buy_stop=_optional_decimal(normalized, "valBuyStop", "buyStop", "stopBuy"),
            sell_stop=_optional_decimal(normalized, "valSellStop", "sellStop", "stopSell"),
            row_timestamp=str(normalized.get("updated_at") or normalized.get("created_at") or ""),
        )


class ParameterSource(Protocol):
    def latest(self) -> SheetParameters: ...


class GoogleSheetParameterSource:
    """Read the newest non-empty parameter row from a private worksheet."""

    def __init__(self, *, tab_name: str = "xauusd_calculation_parameters") -> None:
        self.tab_name = tab_name

    def latest(self) -> SheetParameters:
        try:
            rows = PrivateGoogleSheetsService().read_rows(self.tab_name, limit=20)
        except Exception as exc:
            if _is_unauthorized(exc):
                raise UnauthorizedError("Google Sheets authentication failed.") from exc
            raise DataUnavailableError("Google Sheet is unavailable.") from exc
        for row in reversed(rows):
            if any(str(value).strip() for value in row.values()):
                return SheetParameters.from_row(row)
        raise DataUnavailableError("Google Sheet has no parameter rows.")


class PriceSource(Protocol):
    def latest(self) -> tuple[Decimal, datetime, str]: ...


class LiveXauUsdPriceSource:
    """GoldAPI first, Yahoo Finance fallback, with 401 fail-closed handling."""

    def __init__(self, *, goldapi_key: str = "", symbol: str = "GC=F") -> None:
        self.goldapi_key = goldapi_key.strip()
        self.symbol = symbol.strip() or "GC=F"

    def latest(self) -> tuple[Decimal, datetime, str]:
        if self.goldapi_key:
            try:
                response = requests.get(
                    "https://www.goldapi.io/api/XAU/USD",
                    headers={"x-access-token": self.goldapi_key},
                    timeout=8,
                )
                if response.status_code in {401, 403}:
                    raise UnauthorizedError("GoldAPI authentication failed.")
                response.raise_for_status()
                price = _decimal(response.json().get("price"), "GoldAPI price")
                stamp = response.json().get("timestamp")
                observed = datetime.fromtimestamp(stamp, tz=timezone.utc) if stamp else datetime.now(timezone.utc)
                return price, observed, "GOLDAPI:XAU/USD"
            except UnauthorizedError:
                raise
            except requests.RequestException as exc:
                logger.warning("GoldAPI unavailable; trying Yahoo fallback: {}", exc)
        try:
            history = yf.Ticker(self.symbol).history(period="1d", interval="1m", auto_adjust=False, actions=False)
            if history.empty or "Close" not in history:
                raise DataUnavailableError("Yahoo returned no XAUUSD price.")
            close = history["Close"].dropna()
            if close.empty:
                raise DataUnavailableError("Yahoo returned no valid XAUUSD close.")
            observed = close.index[-1].to_pydatetime()
            if observed.tzinfo is None:
                observed = observed.replace(tzinfo=timezone.utc)
            return _decimal(close.iloc[-1], "Yahoo price"), observed, f"YAHOO:{self.symbol}"
        except UnauthorizedError:
            raise
        except Exception as exc:
            raise DataUnavailableError("Live XAUUSD price is unavailable.") from exc


class Notifier(Protocol):
    def notify(self, title: str, message: str) -> None: ...


class MacOSNotifier:
    def notify(self, title: str, message: str) -> None:
        if not shutil.which("osascript"):
            return
        script = "display notification %s with title %s" % (
            _osascript_string(message), _osascript_string(title)
        )
        try:
            subprocess.run(["osascript", "-e", script], check=False, timeout=5)
        except (OSError, subprocess.SubprocessError):
            logger.warning("macOS notification failed")


@dataclass
class PaperPosition:
    side: str
    entry: Decimal
    opened_at: datetime
    targets: tuple[Decimal, ...]
    stop: Decimal | None
    next_target: int = 0


@dataclass
class PaperTrader:
    parameter_source: ParameterSource
    price_source: PriceSource
    notifier: Notifier | None = None
    enabled: bool = True
    position: PaperPosition | None = None
    events: list[str] = field(default_factory=list)

    def tick(self) -> str:
        if not self.enabled or os.getenv("PAPER_TRADING", "true").lower() not in {"1", "true", "yes", "on"}:
            return self._event("SKIP paper trading disabled")
        try:
            params = self.parameter_source.latest()
            price, observed, source = self.price_source.latest()
        except UnauthorizedError as exc:
            return self._event(f"BLOCK unauthorized provider: {exc}")
        except DataUnavailableError as exc:
            return self._event(f"WAIT data unavailable: {exc}")
        if self.position is None:
            if price <= params.buy_base:
                return self._open("BUY", price, observed, params.buy_targets, params.buy_stop, source)
            if price >= params.sell_base:
                return self._open("SELL", price, observed, params.sell_targets, params.sell_stop, source)
            return self._event(f"WATCH {price} between BUY {params.buy_base} and SELL {params.sell_base} ({source})")
        return self._manage(price, observed, params)

    def _open(self, side: str, price: Decimal, observed: datetime, targets: tuple[Decimal, ...], stop: Decimal | None, source: str) -> str:
        self.position = PaperPosition(side, price, observed, targets, stop)
        return self._event(f"PAPER OPEN {side} entry={price} time={observed.isoformat()} source={source}", notify=True)

    def _manage(self, price: Decimal, observed: datetime, params: SheetParameters) -> str:
        assert self.position is not None
        position = self.position
        if position.stop is not None and ((position.side == "BUY" and price <= position.stop) or (position.side == "SELL" and price >= position.stop)):
            message = self._event(f"PAPER STOP {position.side} exit={price} time={observed.isoformat()}", notify=True)
            self.position = None
            return message
        hit_message: str | None = None
        while position.next_target < len(position.targets):
            target = position.targets[position.next_target]
            hit = price >= target if position.side == "BUY" else price <= target
            if not hit:
                break
            position.next_target += 1
            hit_message = self._event(f"PAPER TARGET {position.side} T{position.next_target}={target} price={price} time={observed.isoformat()}", notify=True)
        if hit_message:
            return hit_message
        return self._event(f"PAPER HOLD {position.side} entry={position.entry} price={price}")

    def _event(self, message: str, *, notify: bool = False) -> str:
        logger.info(message)
        self.events.append(message)
        if notify and self.notifier:
            self.notifier.notify("XAUUSD paper trade", message)
        return message


def run_forever(trader: PaperTrader, *, interval_seconds: int = 60, stop: Callable[[], bool] | None = None) -> None:
    """Run until interrupted; every provider failure is isolated to its tick."""
    while not (stop and stop()):
        started = monotonic()
        try:
            trader.tick()
        except Exception:
            logger.exception("Paper-trader tick failed; continuing safely")
        sleep(max(1, interval_seconds - int(monotonic() - started)))


def _is_unauthorized(exc: Exception) -> bool:
    response = getattr(exc, "response", None)
    return getattr(response, "status_code", None) in {401, 403} or "401" in str(exc) or "unauthorized" in str(exc).lower()


def _osascript_string(value: str) -> str:
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'
