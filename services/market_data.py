"""XAUUSD market-price retrieval and Supabase persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from threading import Lock
from typing import Any

from loguru import logger
import requests
from supabase import Client, create_client
import yfinance as yf

from config import get_settings


@dataclass(frozen=True)
class MarketPrice:
    """Normalized current market price."""

    symbol: str
    price: Decimal
    observed_at: datetime
    source: str


class MarketDataService:
    """Fetch XAUUSD prices and persist enriched market signals."""

    _price_cache_lock = Lock()
    _last_successful_price: MarketPrice | None = None

    def __init__(self, supabase: Client | None = None) -> None:
        settings = get_settings()
        self._symbol = settings.xauusd_symbol
        self._goldapi_key = settings.goldapi_key
        self._supabase = supabase or create_client(
            settings.supabase_url,
            settings.supabase_key,
        )

    def fetch_current_price(self) -> MarketPrice | None:
        """Fetch the latest available quote without crashing the pipeline."""
        if self._goldapi_key:
            spot_price = self._fetch_goldapi_price()
            if spot_price is not None:
                return self._remember_price(spot_price)
            logger.warning(
                "GoldAPI failed; falling back to Yahoo symbol {}",
                self._symbol,
            )
        yahoo_price = self._fetch_yahoo_price()
        if yahoo_price is not None:
            return self._remember_price(yahoo_price)
        return self._cached_price()

    def _fetch_goldapi_price(self) -> MarketPrice | None:
        """Fetch exact XAU/USD spot pricing from GoldAPI."""
        try:
            response = requests.get(
                "https://www.goldapi.io/api/XAU/USD",
                headers={
                    "x-access-token": self._goldapi_key,
                    "Content-Type": "application/json",
                },
                timeout=2,
            )
            response.raise_for_status()
            payload = response.json()
            price = Decimal(str(payload["price"]))
            timestamp = payload.get("timestamp")
            observed_at = (
                datetime.fromtimestamp(timestamp, tz=timezone.utc)
                if timestamp
                else datetime.now(timezone.utc)
            )
            logger.info(
                "GoldAPI XAU/USD spot price fetched: price={} time={}",
                price,
                observed_at.isoformat(),
            )
            return MarketPrice(
                symbol="XAUUSD",
                price=price,
                observed_at=observed_at,
                source="GOLDAPI:XAU/USD",
            )
        except Exception as exc:
            logger.warning("GoldAPI XAU/USD request failed: {}", exc)
            return None

    def _fetch_yahoo_price(self) -> MarketPrice | None:
        """Fetch the configured Yahoo gold instrument as a fallback."""
        try:
            ticker = yf.Ticker(self._symbol)
            history = ticker.history(
                period="1d",
                interval="1m",
                auto_adjust=False,
                actions=False,
            )
            if history.empty:
                history = ticker.history(
                    period="5d",
                    interval="1d",
                    auto_adjust=False,
                    actions=False,
                )
            if history.empty or "Close" not in history:
                logger.error(
                    "No XAUUSD price data returned for symbol {}",
                    self._symbol,
                )
                return None

            close_series = history["Close"].dropna()
            if close_series.empty:
                logger.error(
                    "XAUUSD response contained no valid close price: {}",
                    self._symbol,
                )
                return None

            raw_timestamp = close_series.index[-1]
            observed_at = raw_timestamp.to_pydatetime()
            if observed_at.tzinfo is None:
                observed_at = observed_at.replace(tzinfo=timezone.utc)
            price = Decimal(str(float(close_series.iloc[-1])))
            logger.info(
                "Market price fetched: symbol={} price={} time={}",
                self._symbol,
                price,
                observed_at.isoformat(),
            )
            return MarketPrice(
                symbol="XAUUSD",
                price=price,
                observed_at=observed_at,
                source=f"YAHOO_FINANCE:{self._symbol}",
            )
        except Exception as exc:
            logger.warning(
                "Yahoo XAUUSD request failed for {}: {}",
                self._symbol,
                exc,
            )
            return None

    @classmethod
    def _remember_price(cls, price: MarketPrice) -> MarketPrice:
        """Cache the last successful quote for transient provider outages."""
        with cls._price_cache_lock:
            cls._last_successful_price = price
        return price

    @classmethod
    def _cached_price(cls) -> MarketPrice | None:
        """Return a clearly labelled cached quote instead of raising."""
        with cls._price_cache_lock:
            cached = cls._last_successful_price
        if cached is None:
            logger.error(
                "All XAUUSD providers failed and no cached quote is available"
            )
            return None
        logger.warning(
            "Using cached XAUUSD quote from {} observed at {}",
            cached.source,
            cached.observed_at.isoformat(),
        )
        return MarketPrice(
            symbol=cached.symbol,
            price=cached.price,
            observed_at=cached.observed_at,
            source=f"CACHED:{cached.source}",
        )

    def signal_exists(self, external_key: str) -> bool:
        """Check whether a Sheet instruction was already persisted."""
        try:
            response = (
                self._supabase.table("market_signals")
                .select("id")
                .eq("external_key", external_key)
                .limit(1)
                .execute()
            )
            return bool(response.data)
        except Exception:
            logger.exception(
                "Unable to check market signal key {}",
                external_key,
            )
            return False

    def insert_signal(
        self,
        market_price: MarketPrice,
        signal_type: str,
        target_price: Decimal | None,
        stop_loss: Decimal | None,
        sheet_label: str,
        external_key: str,
    ) -> dict[str, Any] | None:
        """Insert a normalized BUY/SELL signal into Supabase."""
        direction = signal_type.strip().upper()
        if direction not in {"BUY", "SELL"}:
            logger.error("Rejected unsupported signal direction: {}", direction)
            return None

        record = {
            "symbol": market_price.symbol,
            "price": float(market_price.price),
            "signal_type": direction,
            "target_price": (
                float(target_price) if target_price is not None else None
            ),
            "stop_loss": (
                float(stop_loss) if stop_loss is not None else None
            ),
            "source": market_price.source,
            "sheet_label": sheet_label,
            "external_key": external_key,
            "signal_time": market_price.observed_at.isoformat(),
        }
        try:
            response = (
                self._supabase.table("market_signals")
                .insert(record)
                .execute()
            )
        except Exception:
            logger.exception(
                "Failed to insert {} market signal into Supabase",
                direction,
            )
            return None

        inserted = response.data[0] if response.data else record
        logger.info(
            "Market signal inserted: id={} direction={} price={}",
            inserted.get("id"),
            direction,
            market_price.price,
        )
        return inserted
