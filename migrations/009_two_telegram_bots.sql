-- Phase P6.x: document and index two-bot Telegram Master AI routing.
-- Additive only. Does not touch TELEGRAM_BOT_TOKEN, MASTER_AI_TELEGRAM_BOT_TOKEN,
-- Railway variables, Supabase credentials, service_account.json, or .env.

BEGIN;

CREATE INDEX IF NOT EXISTS master_ai_events_telegram_commands_idx
    ON public.master_ai_events(created_at DESC)
    WHERE event_type IN ('TELEGRAM_MASTER_COMMAND', 'TELEGRAM_MASTER_WEBHOOK');

COMMENT ON INDEX public.master_ai_events_telegram_commands_idx IS
    'Supports audit lookup for Master AI Telegram admin command events from /webhooks/telegram/master.';

COMMIT;
