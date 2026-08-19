DROP INDEX IF EXISTS public.content_seo_validation_issues_gin;
DROP INDEX IF EXISTS public.content_seo_score_idx;

ALTER TABLE public.content_seo
    DROP COLUMN IF EXISTS updated_by,
    DROP COLUMN IF EXISTS seo_validation_issues,
    DROP COLUMN IF EXISTS seo_score,
    DROP COLUMN IF EXISTS sitemap_included,
    DROP COLUMN IF EXISTS robots_follow,
    DROP COLUMN IF EXISTS robots_index,
    DROP COLUMN IF EXISTS canonical_url,
    DROP COLUMN IF EXISTS secondary_keywords;
