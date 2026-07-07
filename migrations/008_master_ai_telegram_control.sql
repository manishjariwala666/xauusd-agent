-- Phase P6.x: Telegram Master AI command observability additions.
-- Additive only. Does not change Telegram tokens, existing agents, or reply-agent behavior.

BEGIN;

CREATE INDEX IF NOT EXISTS master_ai_events_type_created_idx
    ON public.master_ai_events(event_type, created_at DESC);

COMMENT ON INDEX public.master_ai_events_type_created_idx IS
    'Supports dashboard/audit lookup for Telegram Master AI command events.';

COMMENT ON TABLE public.master_ai_events IS
    'Dashboard and notification-safe Master AI orchestration events, including Telegram admin command events.';

COMMIT;
