-- Phase P6.1: align database agent availability with the canonical Master AI registry.
-- "Enabled" means the agent is available to the approved execution path.
-- It does NOT bypass capability/approval policy or create background schedules.
-- External-impact and critical actions remain owner-approval gated.

BEGIN;

INSERT INTO public.ai_agents (
    agent_key,
    display_name,
    display_order,
    is_enabled,
    status,
    updated_at
)
VALUES
    ('master_ai', 'Venus Master AI', 1, TRUE, 'IDLE', NOW()),
    ('signal_agent', 'Venus Signal Agent', 10, TRUE, 'IDLE', NOW()),
    ('whatsapp_reply_agent', 'Venus WhatsApp Reply Agent', 20, TRUE, 'IDLE', NOW()),
    ('telegram_reply_agent', 'Venus Telegram Reply Agent', 30, TRUE, 'IDLE', NOW()),
    ('ai_blog_agent', 'Venus Blog Agent', 40, TRUE, 'IDLE', NOW()),
    ('market_data_agent', 'Venus Market Data Agent', 50, TRUE, 'IDLE', NOW()),
    ('customer_support_agent', 'Venus Customer Support Agent', 60, TRUE, 'IDLE', NOW()),
    ('marketing_strategy_agent', 'Venus Marketing Strategy Agent', 70, TRUE, 'IDLE', NOW()),
    ('social_media_agent', 'Venus Social Media Agent', 80, TRUE, 'IDLE', NOW()),
    ('master_publish_approval_agent', 'Venus Master Publish Approval Agent', 90, TRUE, 'IDLE', NOW()),
    ('master_content_review_agent', 'Venus Master Content Review Agent', 100, TRUE, 'IDLE', NOW()),
    ('cms_editor_agent', 'Venus CMS Editor Agent', 110, TRUE, 'IDLE', NOW()),
    ('image_agent', 'Venus Image Agent', 120, TRUE, 'IDLE', NOW()),
    ('announcement_agent', 'Venus Announcement Agent', 130, TRUE, 'IDLE', NOW()),
    ('seo_agent', 'Venus SEO Agent', 140, TRUE, 'IDLE', NOW()),
    ('macro_ai_agent', 'Venus Macro AI', 150, TRUE, 'IDLE', NOW()),
    ('economic_calendar_ai_agent', 'Venus Economic Calendar AI', 160, TRUE, 'IDLE', NOW()),
    ('website_health_agent', 'Venus Website Health Agent', 170, TRUE, 'IDLE', NOW()),
    ('delivery_monitor_agent', 'Venus Delivery Monitor Agent', 180, TRUE, 'IDLE', NOW()),
    ('scheduler_agent', 'Venus Scheduler Agent', 190, TRUE, 'IDLE', NOW()),
    ('admin_support_agent', 'Venus Admin Support Agent', 200, TRUE, 'IDLE', NOW()),
    ('report_agent', 'Venus Report Agent', 210, TRUE, 'IDLE', NOW())
ON CONFLICT (agent_key) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    display_order = EXCLUDED.display_order,
    is_enabled = TRUE,
    updated_at = NOW();

-- Preserve command-mode scheduling: only the explicitly configured signal
-- schedule may remain enabled in the background.
UPDATE public.ai_agent_schedules s
SET is_enabled = CASE
        WHEN a.agent_key = 'signal_agent' THEN s.is_enabled
        ELSE FALSE
    END,
    updated_at = NOW()
FROM public.ai_agents a
WHERE a.id = s.agent_id;

COMMIT;
