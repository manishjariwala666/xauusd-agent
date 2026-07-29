BEGIN;

ALTER TABLE public.market_signals
    DROP COLUMN IF EXISTS target_6,
    DROP COLUMN IF EXISTS target_5;

COMMIT;
