BEGIN;

ALTER TABLE public.content_categories
    ADD COLUMN IF NOT EXISTS route_path TEXT,
    ADD COLUMN IF NOT EXISTS source_type TEXT NOT NULL DEFAULT 'content_items',
    ADD COLUMN IF NOT EXISTS meta_description TEXT;

UPDATE public.content_categories
SET route_path = CASE
        WHEN slug = 'xauusd-signals' THEN '/signals/xauusd'
        WHEN slug = 'analysis-department' THEN '/market-analysis'
        WHEN slug = 'crypto-signals' THEN '/market-analysis/crypto'
        WHEN slug = 'ai-blog' THEN '/blog'
        ELSE '/category/' || slug
    END
WHERE route_path IS NULL OR route_path = '';

UPDATE public.content_categories
SET source_type = CASE
        WHEN slug = 'xauusd-signals' THEN 'market_signals'
        ELSE 'content_items'
    END
WHERE source_type IS NULL OR source_type = '';

UPDATE public.content_categories
SET meta_description = COALESCE(NULLIF(meta_description, ''), description)
WHERE meta_description IS NULL OR meta_description = '';

ALTER TABLE public.content_categories
    DROP CONSTRAINT IF EXISTS content_categories_source_type_check;

ALTER TABLE public.content_categories
    ADD CONSTRAINT content_categories_source_type_check CHECK (
        source_type IN (
            'content_items',
            'market_signals',
            'site_settings',
            'external_api'
        )
    );

CREATE INDEX IF NOT EXISTS content_categories_source_type_idx
    ON public.content_categories (source_type, display_order);

COMMIT;
