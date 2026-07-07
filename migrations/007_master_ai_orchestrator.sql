-- Phase P6.0: Master AI Orchestrator schema-only additions.
-- Additive migration only: no existing agent behavior is changed.
-- Existing agents remain worker agents and existing direct execution paths remain valid.

BEGIN;

CREATE TABLE IF NOT EXISTS public.master_ai_tasks (
    id BIGSERIAL PRIMARY KEY,
    task_key TEXT UNIQUE,
    task_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    source TEXT NOT NULL,
    requested_by BIGINT NULL,
    risk_level TEXT NOT NULL DEFAULT 'LOW',
    input_payload_redacted JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'CREATED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT master_ai_tasks_status_check CHECK (
        status IN (
            'CREATED', 'PLANNING', 'PLAN_READY', 'WAITING_APPROVAL',
            'RUNNING', 'COMPLETED', 'PARTIAL_SUCCESS', 'FAILED',
            'CANCELLED', 'BLOCKED'
        )
    ),
    CONSTRAINT master_ai_tasks_risk_check CHECK (
        risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')
    )
);

CREATE TABLE IF NOT EXISTS public.master_ai_runs (
    id BIGSERIAL PRIMARY KEY,
    task_id BIGINT NOT NULL REFERENCES public.master_ai_tasks(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'CREATED',
    planner_version TEXT NOT NULL DEFAULT 'p6.v1',
    plan_summary TEXT,
    final_summary TEXT,
    safe_error TEXT,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    duration_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT master_ai_runs_status_check CHECK (
        status IN (
            'CREATED', 'PLANNING', 'PLAN_READY', 'WAITING_APPROVAL',
            'RUNNING', 'COMPLETED', 'PARTIAL_SUCCESS', 'FAILED',
            'CANCELLED', 'BLOCKED'
        )
    )
);

CREATE TABLE IF NOT EXISTS public.master_ai_execution_steps (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES public.master_ai_runs(id) ON DELETE CASCADE,
    step_key TEXT NOT NULL,
    agent_id BIGINT NULL REFERENCES public.ai_agents(id) ON DELETE SET NULL,
    agent_key TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    can_run_parallel BOOLEAN NOT NULL DEFAULT FALSE,
    approval_required BOOLEAN NOT NULL DEFAULT FALSE,
    retry_policy JSONB NOT NULL DEFAULT '{}'::jsonb,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 1,
    input_payload_redacted JSONB NOT NULL DEFAULT '{}'::jsonb,
    output_summary TEXT,
    output_payload_redacted JSONB NOT NULL DEFAULT '{}'::jsonb,
    records_processed INTEGER NOT NULL DEFAULT 0,
    db_tables_written TEXT[] NOT NULL DEFAULT '{}',
    external_services_called TEXT[] NOT NULL DEFAULT '{}',
    generated_files JSONB NOT NULL DEFAULT '[]'::jsonb,
    setup_warnings TEXT[] NOT NULL DEFAULT '{}',
    safe_error TEXT,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    duration_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(run_id, step_key),
    CONSTRAINT master_ai_steps_status_check CHECK (
        status IN (
            'PENDING', 'READY', 'WAITING_APPROVAL', 'RUNNING',
            'COMPLETED', 'FAILED', 'SKIPPED', 'CANCELLED', 'BLOCKED'
        )
    )
);

CREATE TABLE IF NOT EXISTS public.master_ai_execution_edges (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES public.master_ai_runs(id) ON DELETE CASCADE,
    from_step_id BIGINT NOT NULL REFERENCES public.master_ai_execution_steps(id) ON DELETE CASCADE,
    to_step_id BIGINT NOT NULL REFERENCES public.master_ai_execution_steps(id) ON DELETE CASCADE,
    edge_type TEXT NOT NULL DEFAULT 'DEPENDS_ON',
    condition JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(from_step_id, to_step_id),
    CONSTRAINT master_ai_edges_type_check CHECK (
        edge_type IN ('DEPENDS_ON', 'CONDITIONAL', 'RETRY_AFTER', 'APPROVAL_UNLOCKS')
    )
);

CREATE TABLE IF NOT EXISTS public.master_ai_context_versions (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES public.master_ai_runs(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    context_redacted JSONB NOT NULL DEFAULT '{}'::jsonb,
    changed_by_step_id BIGINT NULL REFERENCES public.master_ai_execution_steps(id) ON DELETE SET NULL,
    change_summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(run_id, version_number)
);

CREATE TABLE IF NOT EXISTS public.master_ai_memory_entries (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES public.master_ai_runs(id) ON DELETE CASCADE,
    step_id BIGINT NULL REFERENCES public.master_ai_execution_steps(id) ON DELETE SET NULL,
    entry_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    data_redacted JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT master_ai_memory_entry_type_check CHECK (
        entry_type IN (
            'TASK_RECEIVED', 'PLAN_CREATED', 'DECISION', 'STEP_STARTED',
            'STEP_COMPLETED', 'STEP_FAILED', 'APPROVAL_REQUESTED',
            'APPROVAL_DECISION', 'CONTEXT_UPDATED', 'FINAL_SUMMARY'
        )
    )
);

CREATE TABLE IF NOT EXISTS public.master_ai_agent_messages (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES public.master_ai_runs(id) ON DELETE CASCADE,
    from_step_id BIGINT NULL REFERENCES public.master_ai_execution_steps(id) ON DELETE SET NULL,
    to_step_id BIGINT NULL REFERENCES public.master_ai_execution_steps(id) ON DELETE SET NULL,
    from_agent_key TEXT NOT NULL,
    to_agent_key TEXT NOT NULL,
    message_type TEXT NOT NULL,
    payload_redacted JSONB NOT NULL DEFAULT '{}'::jsonb,
    summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.master_ai_approvals (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES public.master_ai_runs(id) ON DELETE CASCADE,
    step_id BIGINT NULL REFERENCES public.master_ai_execution_steps(id) ON DELETE CASCADE,
    approval_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    reason TEXT NOT NULL,
    requested_by TEXT NOT NULL DEFAULT 'MASTER_AI',
    decided_by BIGINT NULL,
    decision_note TEXT,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decided_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    CONSTRAINT master_ai_approval_status_check CHECK (
        status IN ('PENDING', 'APPROVED', 'REJECTED', 'EXPIRED', 'CANCELLED')
    )
);

CREATE TABLE IF NOT EXISTS public.master_ai_events (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES public.master_ai_runs(id) ON DELETE CASCADE,
    step_id BIGINT NULL REFERENCES public.master_ai_execution_steps(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'INFO',
    message TEXT NOT NULL,
    metadata_redacted JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT master_ai_events_severity_check CHECK (
        severity IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
    )
);

ALTER TABLE public.ai_agent_runs
    ADD COLUMN IF NOT EXISTS master_run_id BIGINT NULL REFERENCES public.master_ai_runs(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS master_step_id BIGINT NULL REFERENCES public.master_ai_execution_steps(id) ON DELETE SET NULL;

ALTER TABLE public.ai_agent_jobs
    ADD COLUMN IF NOT EXISTS master_run_id BIGINT NULL REFERENCES public.master_ai_runs(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS master_step_id BIGINT NULL REFERENCES public.master_ai_execution_steps(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS master_ai_tasks_status_created_idx
    ON public.master_ai_tasks(status, created_at DESC);

CREATE INDEX IF NOT EXISTS master_ai_runs_task_status_idx
    ON public.master_ai_runs(task_id, status, created_at DESC);

CREATE INDEX IF NOT EXISTS master_ai_runs_status_created_idx
    ON public.master_ai_runs(status, created_at DESC);

CREATE INDEX IF NOT EXISTS master_ai_steps_run_status_idx
    ON public.master_ai_execution_steps(run_id, status, created_at);

CREATE INDEX IF NOT EXISTS master_ai_steps_agent_status_idx
    ON public.master_ai_execution_steps(agent_key, status, created_at DESC);

CREATE INDEX IF NOT EXISTS master_ai_edges_run_to_idx
    ON public.master_ai_execution_edges(run_id, to_step_id);

CREATE INDEX IF NOT EXISTS master_ai_context_run_version_idx
    ON public.master_ai_context_versions(run_id, version_number DESC);

CREATE INDEX IF NOT EXISTS master_ai_memory_run_created_idx
    ON public.master_ai_memory_entries(run_id, created_at DESC);

CREATE INDEX IF NOT EXISTS master_ai_messages_run_agents_idx
    ON public.master_ai_agent_messages(run_id, from_agent_key, to_agent_key, created_at DESC);

CREATE INDEX IF NOT EXISTS master_ai_approvals_status_idx
    ON public.master_ai_approvals(status, requested_at DESC);

CREATE INDEX IF NOT EXISTS master_ai_events_run_created_idx
    ON public.master_ai_events(run_id, created_at DESC);

CREATE INDEX IF NOT EXISTS ai_agent_runs_master_run_idx
    ON public.ai_agent_runs(master_run_id, master_step_id);

CREATE INDEX IF NOT EXISTS ai_agent_jobs_master_run_idx
    ON public.ai_agent_jobs(master_run_id, master_step_id);

ALTER TABLE public.master_ai_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.master_ai_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.master_ai_execution_steps ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.master_ai_execution_edges ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.master_ai_context_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.master_ai_memory_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.master_ai_agent_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.master_ai_approvals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.master_ai_events ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.master_ai_tasks FROM anon, authenticated;
REVOKE ALL ON TABLE public.master_ai_runs FROM anon, authenticated;
REVOKE ALL ON TABLE public.master_ai_execution_steps FROM anon, authenticated;
REVOKE ALL ON TABLE public.master_ai_execution_edges FROM anon, authenticated;
REVOKE ALL ON TABLE public.master_ai_context_versions FROM anon, authenticated;
REVOKE ALL ON TABLE public.master_ai_memory_entries FROM anon, authenticated;
REVOKE ALL ON TABLE public.master_ai_agent_messages FROM anon, authenticated;
REVOKE ALL ON TABLE public.master_ai_approvals FROM anon, authenticated;
REVOKE ALL ON TABLE public.master_ai_events FROM anon, authenticated;

COMMENT ON TABLE public.master_ai_tasks IS 'Phase P6.0 high-level task intake for the Master AI Orchestrator.';
COMMENT ON TABLE public.master_ai_runs IS 'Phase P6.0 orchestration run records; no execution logic is enabled by this migration.';
COMMENT ON TABLE public.master_ai_execution_steps IS 'Phase P6.0 execution graph nodes linking future master orchestration to existing worker agents.';
COMMENT ON TABLE public.master_ai_execution_edges IS 'Phase P6.0 execution graph dependency edges.';
COMMENT ON TABLE public.master_ai_context_versions IS 'Phase P6.0 redacted shared task context version history.';
COMMENT ON TABLE public.master_ai_memory_entries IS 'Phase P6.0 safe execution memory; never stores credentials or private reasoning.';
COMMENT ON TABLE public.master_ai_agent_messages IS 'Phase P6.0 redacted agent-to-agent messages mediated by the Master AI.';
COMMENT ON TABLE public.master_ai_approvals IS 'Phase P6.0 human approval gates for orchestrated execution.';
COMMENT ON TABLE public.master_ai_events IS 'Phase P6.0 dashboard and notification-safe orchestration events.';

COMMIT;
