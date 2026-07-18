-- Phase 1 rollback. Run manually only after the Next.js admin is disabled.

BEGIN;

DROP TABLE IF EXISTS public.admin_auth_audit_events;
DROP TABLE IF EXISTS public.admin_login_attempts;
DROP TABLE IF EXISTS public.admin_sessions;

COMMIT;
