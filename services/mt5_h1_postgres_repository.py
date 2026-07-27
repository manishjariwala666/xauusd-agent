"""PostgreSQL repository for MT5 XAUUSD H1 candles.

This adapter never creates tables or runs migrations.
"""

from __future__ import annotations

from sqlalchemy import text

from core.database import session_scope
from services.mt5_h1_repository import H1Candle


class PostgresH1Repository:
    def event_exists(self, source_event_id: str) -> bool:
        with session_scope() as session:
            value = session.execute(
                text(
                    """
                    SELECT 1
                    FROM public.mt5_h1_candles
                    WHERE source_event_id = :event_id
                    LIMIT 1
                    """
                ),
                {"event_id": source_event_id},
            ).scalar_one_or_none()

        return value is not None

    def save_candle(self, candle: H1Candle) -> H1Candle:
        with session_scope() as session:
            session.execute(
                text(
                    """
                    INSERT INTO public.mt5_h1_candles (
                        symbol,
                        broker_symbol,
                        broker_server,
                        candle_start_utc,
                        open,
                        high,
                        low,
                        close,
                        source_event_id,
                        received_at_utc,
                        source
                    ) VALUES (
                        :symbol,
                        :broker_symbol,
                        :broker_server,
                        :candle_start,
                        :open,
                        :high,
                        :low,
                        :close,
                        :event_id,
                        :received_at,
                        'MT5'
                    )
                    ON CONFLICT (
                        symbol,
                        broker_server,
                        candle_start_utc
                    ) DO UPDATE SET
                        broker_symbol = EXCLUDED.broker_symbol,
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        source_event_id = EXCLUDED.source_event_id,
                        received_at_utc = EXCLUDED.received_at_utc,
                        source = 'MT5',
                        updated_at = NOW()
                    WHERE EXCLUDED.received_at_utc
                          >= public.mt5_h1_candles.received_at_utc
                    """
                ),
                {
                    "symbol": candle.symbol,
                    "broker_symbol": candle.broker_symbol,
                    "broker_server": candle.broker_server,
                    "candle_start": candle.candle_start_utc,
                    "open": candle.open,
                    "high": candle.high,
                    "low": candle.low,
                    "close": candle.close,
                    "event_id": candle.source_event_id,
                    "received_at": candle.received_at_utc,
                },
            )

        return candle

    def latest_candle(self, symbol: str) -> H1Candle | None:
        with session_scope() as session:
            row = (
                session.execute(
                    text(
                        """
                        SELECT
                            symbol,
                            broker_symbol,
                            broker_server,
                            candle_start_utc,
                            open,
                            high,
                            low,
                            close,
                            source_event_id,
                            received_at_utc,
                            source
                        FROM public.mt5_h1_candles
                        WHERE symbol = :symbol
                        ORDER BY
                            candle_start_utc DESC,
                            received_at_utc DESC
                        LIMIT 1
                        """
                    ),
                    {"symbol": symbol.strip().upper()},
                )
                .mappings()
                .first()
            )

        if not row:
            return None

        return H1Candle(
            symbol=str(row["symbol"]),
            broker_symbol=str(row["broker_symbol"]),
            broker_server=str(row["broker_server"]),
            candle_start_utc=row["candle_start_utc"],
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
            source_event_id=str(row["source_event_id"]),
            received_at_utc=row["received_at_utc"],
            source=str(row["source"] or "MT5"),
        )
