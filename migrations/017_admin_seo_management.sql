-- Phase 3B: additive SEO editing, deterministic scoring, and validation state.

ALTER TABLE public.content_seo
    ADD COLUMN IF NOT EXISTS secondary_keywords JSONB NOT NULL DEFAULT '[]'::JSONB,
    ADD COLUMN IF NOT EXISTS canonical_url TEXT,
    ADD COLUMN IF NOT EXISTS robots_index BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS robots_follow BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS sitemap_included BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS seo_score SMALLINT NOT NULL DEFAULT 0
        CHECK (seo_score BETWEEN 0 AND 100),
    ADD COLUMN IF NOT EXISTS seo_validation_issues JSONB NOT NULL DEFAULT '[]'::JSONB,
    ADD COLUMN IF NOT EXISTS updated_by BIGINT
        REFERENCES public.users(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS content_seo_score_idx
    ON public.content_seo (seo_score, updated_at DESC);

CREATE INDEX IF NOT EXISTS content_seo_validation_issues_gin
    ON public.content_seo USING GIN (seo_validation_issues);
