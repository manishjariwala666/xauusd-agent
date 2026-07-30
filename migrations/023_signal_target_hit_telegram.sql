-- Durable Telegram delivery tracking for automatic target-hit alerts.

BEGIN;

ALTER TABLE public.market_signals
    ADD COLUMN IF NOT EXISTS target_hit_telegram_sent_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS target_hit_telegram_error TEXT;

CREATE INDEX IF NOT EXISTS market_signals_pending_target_alert_idx
    ON public.market_signals (signal_time)
    WHERE signal_type IN ('BUY', 'SELL')
      AND target_price IS NOT NULL
      AND (
          target_hit_telegram_sent_at IS NULL
          OR target_hit_whatsapp_sent_at IS NULL
      );

COMMIT;
