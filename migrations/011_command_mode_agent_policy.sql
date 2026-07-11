-- Command-mode production policy.
--
-- All content/reply/announcement agents remain available for explicit Master AI
-- commands, but background schedules are disabled except one daily XAUUSD
-- signal run at 03:30 Asia/Kolkata.

WITH next_signal_run AS (
    SELECT CASE
        WHEN (
            (timezone('Asia/Kolkata', NOW())::date + TIME '03:30')
            AT TIME ZONE 'Asia/Kolkata'
        ) > NOW()
        THEN (
            (timezone('Asia/Kolkata', NOW())::date + TIME '03:30')
            AT TIME ZONE 'Asia/Kolkata'
        )
        ELSE (
            ((timezone('Asia/Kolkata', NOW())::date + 1) + TIME '03:30')
            AT TIME ZONE 'Asia/Kolkata'
        )
    END AS run_at
),
signal_agent AS (
    UPDATE public.ai_agents
    SET is_enabled = TRUE,
        schedule_minutes = 1440,
        next_scheduled_run_at = (SELECT run_at FROM next_signal_run),
        updated_at = NOW()
    WHERE agent_key = 'signal_agent'
    RETURNING id
)
INSERT INTO public.ai_agent_schedules (
    agent_id,
    interval_minutes,
    payload,
    is_enabled,
    next_run_at
)
SELECT
    id,
    1440,
    '{"scheduled_signal":true,"source":"daily_0330_ist"}'::JSONB,
    TRUE,
    (SELECT run_at FROM next_signal_run)
FROM signal_agent
ON CONFLICT (agent_id) DO UPDATE SET
    interval_minutes = EXCLUDED.interval_minutes,
    payload = EXCLUDED.payload,
    is_enabled = TRUE,
    next_run_at = EXCLUDED.next_run_at,
    updated_at = NOW();

UPDATE public.ai_agent_schedules s
SET is_enabled = FALSE,
    updated_at = NOW()
FROM public.ai_agents a
WHERE a.id = s.agent_id
  AND a.agent_key <> 'signal_agent';

UPDATE public.ai_agents
SET is_enabled = TRUE,
    schedule_minutes = NULL,
    next_scheduled_run_at = NULL,
    updated_at = NOW()
WHERE agent_key <> 'signal_agent';

UPDATE public.ai_agent_jobs j
SET status = 'ERROR',
    finished_at = NOW(),
    last_error = 'Cancelled by command-mode policy: use Master AI commands for non-signal agents.'
FROM public.ai_agents a
WHERE a.id = j.agent_id
  AND a.agent_key <> 'signal_agent'
  AND j.status = 'QUEUED';
