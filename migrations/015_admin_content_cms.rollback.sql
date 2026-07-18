-- Manual Phase 2A rollback. This removes only columns introduced by migration 015.

BEGIN;

DROP INDEX IF EXISTS public.content_items_scheduled_idx;
DROP INDEX IF EXISTS public.content_items_admin_listing_idx;

ALTER TABLE public.content_items
    DROP COLUMN IF EXISTS deleted_by,
    DROP COLUMN IF EXISTS deleted_at,
    DROP COLUMN IF EXISTS scheduled_at;

COMMIT;
