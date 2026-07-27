-- PROPOSAL ONLY.
-- Do not execute without explicit migration approval.

CREATE TABLE public.mt5_h1_candles (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL CHECK (symbol = 'XAUUSD'),
    broker_symbol TEXT NOT NULL,
    broker_server TEXT NOT NULL,
    candle_start_utc TIMESTAMPTZ NOT NULL,
    open NUMERIC(18,6) NOT NULL,
    high NUMERIC(18,6) NOT NULL,
    low NUMERIC(18,6) NOT NULL,
    close NUMERIC(18,6) NOT NULL,
    source_event_id TEXT NOT NULL UNIQUE,
    received_at_utc TIMESTAMPTZ NOT NULL,
    source TEXT NOT NULL DEFAULT 'MT5',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT mt5_h1_valid_range CHECK (
        high >= open
        AND high >= close
        AND high >= low
        AND low <= open
        AND low <= close
        AND low <= high
    ),

    UNIQUE (symbol, broker_server, candle_start_utc)
);

CREATE INDEX mt5_h1_latest_idx
ON public.mt5_h1_candles (
    symbol,
    candle_start_utc DESC,
    received_at_utc DESC
);
