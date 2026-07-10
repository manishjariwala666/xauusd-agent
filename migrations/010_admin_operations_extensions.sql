BEGIN;

ALTER TABLE public.market_signals
    ADD COLUMN IF NOT EXISTS target_1 NUMERIC(18, 6),
    ADD COLUMN IF NOT EXISTS target_2 NUMERIC(18, 6),
    ADD COLUMN IF NOT EXISTS target_3 NUMERIC(18, 6),
    ADD COLUMN IF NOT EXISTS risk_level TEXT,
    ADD COLUMN IF NOT EXISTS timeframe TEXT,
    ADD COLUMN IF NOT EXISTS note TEXT,
    ADD COLUMN IF NOT EXISTS whatsapp_reply TEXT;

UPDATE public.market_signals
SET target_1 = COALESCE(target_1, target_price)
WHERE target_price IS NOT NULL;

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS name TEXT,
    ADD COLUMN IF NOT EXISTS phone TEXT,
    ADD COLUMN IF NOT EXISTS telegram_id TEXT,
    ADD COLUMN IF NOT EXISTS source TEXT;

CREATE INDEX IF NOT EXISTS market_signals_risk_timeframe_idx
    ON public.market_signals (risk_level, timeframe);

CREATE INDEX IF NOT EXISTS users_source_idx
    ON public.users (source);

CREATE INDEX IF NOT EXISTS users_telegram_id_idx
    ON public.users (telegram_id)
    WHERE telegram_id IS NOT NULL;

COMMIT;
