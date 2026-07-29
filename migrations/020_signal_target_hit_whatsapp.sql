-- Durable WhatsApp delivery tracking for automatic signal target hits.

BEGIN;

ALTER TABLE public.market_signals
    ADD COLUMN IF NOT EXISTS target_hit_whatsapp_sent_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS target_hit_whatsapp_error TEXT,
    ADD COLUMN IF NOT EXISTS target_hit_price NUMERIC(18, 6);

CREATE INDEX IF NOT EXISTS market_signals_pending_target_hit_idx
    ON public.market_signals (signal_time)
    WHERE signal_type IN ('BUY', 'SELL')
      AND target_price IS NOT NULL
      AND whatsapp_sent_at IS NOT NULL
      AND target_hit_whatsapp_sent_at IS NULL;

COMMIT;
