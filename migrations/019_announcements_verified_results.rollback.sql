BEGIN;
DROP TABLE IF EXISTS public.verified_results;
DROP INDEX IF EXISTS public.content_items_announcement_public_idx;
DROP INDEX IF EXISTS public.content_items_announcement_admin_idx;
ALTER TABLE public.content_items
    DROP CONSTRAINT IF EXISTS content_items_announcement_dates_check,
    DROP CONSTRAINT IF EXISTS content_items_announcement_audience_check,
    DROP CONSTRAINT IF EXISTS content_items_announcement_priority_check,
    DROP CONSTRAINT IF EXISTS content_items_announcement_type_check,
    DROP COLUMN IF EXISTS updated_by,
    DROP COLUMN IF EXISTS expires_at,
    DROP COLUMN IF EXISTS cta_url,
    DROP COLUMN IF EXISTS cta_label,
    DROP COLUMN IF EXISTS pinned,
    DROP COLUMN IF EXISTS featured,
    DROP COLUMN IF EXISTS announcement_audience,
    DROP COLUMN IF EXISTS announcement_priority,
    DROP COLUMN IF EXISTS announcement_type;
COMMIT;
