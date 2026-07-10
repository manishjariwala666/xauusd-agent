BEGIN;

ALTER TABLE public.content_items
    ADD COLUMN IF NOT EXISTS slug TEXT,
    ADD COLUMN IF NOT EXISTS subcategory TEXT,
    ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'published'));

ALTER TABLE public.content_items
    DROP CONSTRAINT IF EXISTS content_items_type_check;

ALTER TABLE public.content_items
    ADD CONSTRAINT content_items_type_check CHECK (
        content_type IN (
            'BLOG',
            'PAGE',
            'ANNOUNCEMENT',
            'SIGNAL_POST',
            'CATEGORY',
            'SUBCATEGORY',
            'SPECIAL_ZONE',
            'ADVISORY',
            'ANALYSIS',
            'EDUCATION',
            'AI_BLOG',
            'PROFIT_SCREENSHOT'
        )
    );

UPDATE public.content_items ci
SET slug = cs.slug
FROM public.content_seo cs
WHERE cs.content_id = ci.id
  AND ci.slug IS NULL;

UPDATE public.content_items
SET status = CASE
    WHEN is_published = TRUE THEN 'published'
    ELSE 'draft'
END;

CREATE UNIQUE INDEX IF NOT EXISTS content_items_slug_unique_idx
    ON public.content_items (slug)
    WHERE slug IS NOT NULL;

CREATE INDEX IF NOT EXISTS content_items_status_idx
    ON public.content_items (status, updated_at DESC);

CREATE INDEX IF NOT EXISTS content_items_category_subcategory_idx
    ON public.content_items (category_id, subcategory);

COMMIT;
