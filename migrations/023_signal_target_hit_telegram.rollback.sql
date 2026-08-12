BEGIN;

DROP INDEX IF EXISTS public.market_signals_pending_target_alert_idx;

ALTER TABLE public.market_signals
    DROP COLUMN IF EXISTS target_hit_telegram_error,
    DROP COLUMN IF EXISTS target_hit_telegram_sent_at;

COMMIT;
