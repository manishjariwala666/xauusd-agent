BEGIN;

ALTER TABLE public.market_signals
    ADD COLUMN IF NOT EXISTS stop_loss_telegram_sent_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS stop_loss_telegram_error TEXT,
    ADD COLUMN IF NOT EXISTS stop_loss_whatsapp_sent_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS stop_loss_whatsapp_error TEXT;

COMMIT;
