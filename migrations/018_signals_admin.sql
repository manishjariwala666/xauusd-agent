-- Phase 4A: additive Signals Admin and public publishing fields.
-- Apply only to an isolated database until separately approved for production.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE public.market_signals
    ADD COLUMN IF NOT EXISTS public_id UUID NOT NULL DEFAULT gen_random_uuid(),
    ADD COLUMN IF NOT EXISTS market TEXT NOT NULL DEFAULT 'FOREX',
    ADD COLUMN IF NOT EXISTS entry_type TEXT NOT NULL DEFAULT 'MARKET',
    ADD COLUMN IF NOT EXISTS entry_price_min NUMERIC(18, 6),
    ADD COLUMN IF NOT EXISTS entry_price_max NUMERIC(18, 6),
    ADD COLUMN IF NOT EXISTS target_1 NUMERIC(18, 6),
    ADD COLUMN IF NOT EXISTS target_2 NUMERIC(18, 6),
    ADD COLUMN IF NOT EXISTS target_3 NUMERIC(18, 6),
    ADD COLUMN IF NOT EXISTS target_4 NUMERIC(18, 6),
    ADD COLUMN IF NOT EXISTS risk_level TEXT NOT NULL DEFAULT 'MEDIUM',
    ADD COLUMN IF NOT EXISTS confidence_label TEXT,
    ADD COLUMN IF NOT EXISTS timeframe TEXT NOT NULL DEFAULT 'INTRADAY',
    ADD COLUMN IF NOT EXISTS analysis_summary TEXT,
    ADD COLUMN IF NOT EXISTS technical_reason TEXT,
    ADD COLUMN IF NOT EXISTS astrology_reason TEXT,
    ADD COLUMN IF NOT EXISTS risk_note TEXT,
    ADD COLUMN IF NOT EXISTS publication_status TEXT NOT NULL DEFAULT 'DRAFT',
    ADD COLUMN IF NOT EXISTS lifecycle_status TEXT NOT NULL DEFAULT 'DRAFT',
    ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS closed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS outcome TEXT,
    ADD COLUMN IF NOT EXISTS result_points NUMERIC(18, 6),
    ADD COLUMN IF NOT EXISTS result_percentage NUMERIC(9, 4),
    ADD COLUMN IF NOT EXISTS featured BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS created_by BIGINT REFERENCES public.users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS updated_by BIGINT REFERENCES public.users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

UPDATE public.market_signals
SET target_1 = COALESCE(target_1, target_price),
    analysis_summary = COALESCE(analysis_summary, sheet_label),
    risk_note = COALESCE(risk_note, delivery_error)
WHERE target_1 IS NULL OR analysis_summary IS NULL OR risk_note IS NULL;

ALTER TABLE public.market_signals
    DROP CONSTRAINT IF EXISTS market_signals_admin_entry_type_check,
    DROP CONSTRAINT IF EXISTS market_signals_admin_risk_level_check,
    DROP CONSTRAINT IF EXISTS market_signals_admin_publication_check,
    DROP CONSTRAINT IF EXISTS market_signals_admin_lifecycle_check,
    DROP CONSTRAINT IF EXISTS market_signals_admin_range_check,
    DROP CONSTRAINT IF EXISTS market_signals_admin_schedule_check;

ALTER TABLE public.market_signals
    ADD CONSTRAINT market_signals_admin_entry_type_check
        CHECK (entry_type IN ('MARKET', 'LIMIT', 'STOP', 'RANGE')),
    ADD CONSTRAINT market_signals_admin_risk_level_check
        CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH')),
    ADD CONSTRAINT market_signals_admin_publication_check
        CHECK (publication_status IN ('DRAFT', 'SCHEDULED', 'PUBLISHED', 'UNPUBLISHED', 'TRASHED')),
    ADD CONSTRAINT market_signals_admin_lifecycle_check
        CHECK (lifecycle_status IN ('DRAFT', 'SCHEDULED', 'PUBLISHED', 'ACTIVE', 'TARGET_HIT', 'STOPPED', 'CANCELLED', 'EXPIRED', 'CLOSED', 'TRASHED')),
    ADD CONSTRAINT market_signals_admin_range_check
        CHECK (entry_price_min IS NULL OR entry_price_max IS NULL OR entry_price_min <= entry_price_max),
    ADD CONSTRAINT market_signals_admin_schedule_check
        CHECK (expires_at IS NULL OR published_at IS NULL OR expires_at > published_at);

CREATE UNIQUE INDEX IF NOT EXISTS market_signals_public_id_unique
    ON public.market_signals (public_id);
CREATE INDEX IF NOT EXISTS market_signals_admin_list_idx
    ON public.market_signals (publication_status, lifecycle_status, updated_at DESC);
CREATE INDEX IF NOT EXISTS market_signals_public_list_idx
    ON public.market_signals (published_at DESC, id DESC)
    WHERE publication_status = 'PUBLISHED' AND deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS market_signals_symbol_direction_idx
    ON public.market_signals (symbol, signal_type, timeframe);

COMMIT;
