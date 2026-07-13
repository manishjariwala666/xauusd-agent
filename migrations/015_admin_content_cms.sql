-- Phase 2A: additive scheduling and soft-trash support for admin content.

BEGIN;

ALTER TABLE public.content_items
    ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS deleted_by BIGINT
        REFERENCES public.users(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS content_items_admin_listing_idx
    ON public.content_items (content_type, deleted_at, updated_at DESC);

CREATE INDEX IF NOT EXISTS content_items_scheduled_idx
    ON public.content_items (scheduled_at)
    WHERE scheduled_at IS NOT NULL
      AND deleted_at IS NULL
      AND is_published = FALSE;

COMMIT;
