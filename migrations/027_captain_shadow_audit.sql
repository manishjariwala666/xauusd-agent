CREATE TABLE IF NOT EXISTS public.captain_shadow_audits (
    id BIGSERIAL PRIMARY KEY,
    correlation_id TEXT NOT NULL UNIQUE,
    source_interface TEXT NOT NULL CHECK (source_interface IN ('ADMIN', 'TELEGRAM', 'SIGNAL_AGENT', 'SHADOW_API')),
    signal_id BIGINT NULL REFERENCES public.market_signals(id) ON DELETE SET NULL,
    signal_date DATE NOT NULL,
    market_source TEXT NOT NULL,
    day_high NUMERIC(18, 6),
    day_low NUMERIC(18, 6),
    live_cmp NUMERIC(18, 6),
    buy_base NUMERIC(18, 6),
    sell_base NUMERIC(18, 6),
    captain_decision TEXT NOT NULL,
    captain_direction TEXT NOT NULL,
    captain_confidence INTEGER NOT NULL CHECK (captain_confidence BETWEEN 0 AND 100),
    captain_reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    shadow_status TEXT NOT NULL,
    shadow_reason TEXT,
    signal_generated BOOLEAN NOT NULL DEFAULT FALSE,
    delivery_started BOOLEAN NOT NULL DEFAULT FALSE,
    telegram_delivered BOOLEAN,
    whatsapp_delivered BOOLEAN,
    master_ai_summary TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_captain_shadow_audits_created
    ON public.captain_shadow_audits (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_captain_shadow_audits_signal
    ON public.captain_shadow_audits (signal_id, created_at DESC)
    WHERE signal_id IS NOT NULL;

COMMENT ON TABLE public.captain_shadow_audits IS
    'Canonical shared Captain/Shadow/Master AI audit ledger used across Admin, Telegram, and Signal Agent interfaces.';
