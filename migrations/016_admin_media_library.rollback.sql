-- Phase 3A rollback. Existing image_url values are intentionally preserved.

BEGIN;

DROP INDEX IF EXISTS public.content_items_media_id_idx;
ALTER TABLE public.content_items DROP COLUMN IF EXISTS media_id;
DROP TABLE IF EXISTS public.media_assets;

COMMIT;
