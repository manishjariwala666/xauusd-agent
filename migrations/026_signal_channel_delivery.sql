-- Durable per-recipient delivery ledger for Telegram and WhatsApp signals.
-- Idempotent and non-destructive; compatible with existing market_signals rows.

CREATE TABLE IF NOT EXISTS public.signal_channel_deliveries (
    id BIGSERIAL PRIMARY KEY,
    signal_id BIGINT NOT NULL REFERENCES public.market_signals(id) ON DELETE CASCADE,
    channel TEXT NOT NULL CHECK (channel IN ('telegram', 'whatsapp')),
    recipient_hash TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    claimed_at TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,
    external_message_id TEXT,
    error_category TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT signal_channel_deliveries_unique_recipient
        UNIQUE (signal_id, channel, recipient_hash)
);

CREATE INDEX IF NOT EXISTS idx_signal_channel_deliveries_pending
    ON public.signal_channel_deliveries (channel, sent_at, claimed_at, attempts)
    WHERE sent_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_signal_channel_deliveries_signal
    ON public.signal_channel_deliveries (signal_id, channel, sent_at);

COMMENT ON TABLE public.signal_channel_deliveries IS
    'Durable per-recipient idempotency and retry ledger for primary signal delivery.';
