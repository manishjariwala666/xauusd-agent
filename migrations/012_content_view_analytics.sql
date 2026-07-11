BEGIN;

ALTER TABLE public.content_items
    ADD COLUMN IF NOT EXISTS view_count BIGINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS last_viewed_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS content_items_views_idx
    ON public.content_items (view_count DESC, last_viewed_at DESC);

CREATE INDEX IF NOT EXISTS content_items_low_views_idx
    ON public.content_items (view_count ASC, published_at DESC)
    WHERE is_published = TRUE AND is_public = TRUE;

COMMIT;
