-- Roll back only Phase 4A additions. Legacy signal columns remain intact.

BEGIN;

DROP INDEX IF EXISTS public.market_signals_symbol_direction_idx;
DROP INDEX IF EXISTS public.market_signals_public_list_idx;
DROP INDEX IF EXISTS public.market_signals_admin_list_idx;
DROP INDEX IF EXISTS public.market_signals_public_id_unique;

ALTER TABLE public.market_signals
    DROP CONSTRAINT IF EXISTS market_signals_admin_schedule_check,
    DROP CONSTRAINT IF EXISTS market_signals_admin_range_check,
    DROP CONSTRAINT IF EXISTS market_signals_admin_lifecycle_check,
    DROP CONSTRAINT IF EXISTS market_signals_admin_publication_check,
    DROP CONSTRAINT IF EXISTS market_signals_admin_risk_level_check,
    DROP CONSTRAINT IF EXISTS market_signals_admin_entry_type_check,
    DROP COLUMN IF EXISTS deleted_at,
    DROP COLUMN IF EXISTS created_at,
    DROP COLUMN IF EXISTS updated_by,
    DROP COLUMN IF EXISTS created_by,
    DROP COLUMN IF EXISTS featured,
    DROP COLUMN IF EXISTS result_percentage,
    DROP COLUMN IF EXISTS result_points,
    DROP COLUMN IF EXISTS outcome,
    DROP COLUMN IF EXISTS closed_at,
    DROP COLUMN IF EXISTS expires_at,
    DROP COLUMN IF EXISTS scheduled_at,
    DROP COLUMN IF EXISTS published_at,
    DROP COLUMN IF EXISTS lifecycle_status,
    DROP COLUMN IF EXISTS publication_status,
    DROP COLUMN IF EXISTS risk_note,
    DROP COLUMN IF EXISTS astrology_reason,
    DROP COLUMN IF EXISTS technical_reason,
    DROP COLUMN IF EXISTS analysis_summary,
    DROP COLUMN IF EXISTS confidence_label,
    DROP COLUMN IF EXISTS target_4,
    DROP COLUMN IF EXISTS entry_price_max,
    DROP COLUMN IF EXISTS entry_price_min,
    DROP COLUMN IF EXISTS entry_type,
    DROP COLUMN IF EXISTS market,
    DROP COLUMN IF EXISTS public_id;

-- target_1..target_3, risk_level, and timeframe belong to the earlier
-- operations extension migration. Keep them when rolling Phase 4A back.

COMMIT;
