BEGIN;

CREATE TABLE IF NOT EXISTS public.agent_approval_requests (
    id BIGSERIAL PRIMARY KEY,
    request_key TEXT NOT NULL UNIQUE,
    agent_key TEXT NOT NULL,
    action_key TEXT NOT NULL,
    risk_level TEXT NOT NULL
        CHECK (
            risk_level IN (
                'READ_ONLY',
                'LOW',
                'HIGH',
                'CRITICAL',
                'UNKNOWN'
            )
        ),
    status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (
            status IN (
                'PENDING',
                'APPROVED',
                'REJECTED',
                'EXPIRED'
            )
        ),
    request_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
    requested_by BIGINT,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    decided_by BIGINT,
    decided_at TIMESTAMPTZ,
    decision_reason TEXT NOT NULL DEFAULT '',
    version INTEGER NOT NULL DEFAULT 1
        CHECK (version >= 1),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT agent_approval_decision_consistency
        CHECK (
            (
                status = 'PENDING'
                AND decided_by IS NULL
                AND decided_at IS NULL
            )
            OR (
                status IN ('APPROVED', 'REJECTED')
                AND decided_by IS NOT NULL
                AND decided_at IS NOT NULL
            )
            OR status = 'EXPIRED'
        )
);

CREATE INDEX IF NOT EXISTS
    idx_agent_approval_requests_status_created
ON public.agent_approval_requests (
    status,
    created_at DESC
);

CREATE INDEX IF NOT EXISTS
    idx_agent_approval_requests_agent_status
ON public.agent_approval_requests (
    agent_key,
    status
);

CREATE INDEX IF NOT EXISTS
    idx_agent_approval_requests_expires
ON public.agent_approval_requests (
    expires_at
)
WHERE expires_at IS NOT NULL;

CREATE TABLE IF NOT EXISTS public.agent_approval_audit_events (
    id BIGSERIAL PRIMARY KEY,
    approval_id BIGINT NOT NULL
        REFERENCES public.agent_approval_requests(id)
        ON DELETE CASCADE,
    event_type TEXT NOT NULL
        CHECK (
            event_type IN (
                'REQUESTED',
                'APPROVED',
                'REJECTED',
                'UNDONE',
                'EXPIRED',
                'TEST_STARTED',
                'TEST_PASSED',
                'TEST_FAILED'
            )
        ),
    previous_status TEXT,
    next_status TEXT,
    actor_id BIGINT,
    request_id TEXT NOT NULL,
    safe_details JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS
    idx_agent_approval_audit_approval_created
ON public.agent_approval_audit_events (
    approval_id,
    created_at DESC
);

CREATE INDEX IF NOT EXISTS
    idx_agent_approval_audit_request_id
ON public.agent_approval_audit_events (
    request_id
);

COMMIT;
