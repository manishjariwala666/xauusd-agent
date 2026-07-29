BEGIN;

ALTER TABLE public.market_signals
    DROP COLUMN IF EXISTS stop_loss_whatsapp_error,
    DROP COLUMN IF EXISTS stop_loss_whatsapp_sent_at,
    DROP COLUMN IF EXISTS stop_loss_telegram_error,
    DROP COLUMN IF EXISTS stop_loss_telegram_sent_at;

COMMIT;
