-- Secure authentication foundation for AI Market Analytics Pro.
-- Existing columns/data are preserved; no destructive operations are used.

BEGIN;

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS password_hash TEXT,
    ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'USER',
    ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS approval_status TEXT NOT NULL DEFAULT 'PENDING',
    ADD COLUMN IF NOT EXISTS verification_token_hash TEXT,
    ADD COLUMN IF NOT EXISTS verification_expires_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS reset_token_hash TEXT,
    ADD COLUMN IF NOT EXISTS reset_expires_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

UPDATE public.users
SET approval_status = CASE
    WHEN status = 'Approved' THEN 'APPROVED'
    WHEN status = 'Blocked' THEN 'BLOCKED'
    ELSE 'PENDING'
END
WHERE status IS NOT NULL;

ALTER TABLE public.users
    DROP CONSTRAINT IF EXISTS users_role_check,
    DROP CONSTRAINT IF EXISTS users_approval_status_check;

ALTER TABLE public.users
    ADD CONSTRAINT users_role_check
        CHECK (role IN ('ADMIN', 'USER')),
    ADD CONSTRAINT users_approval_status_check
        CHECK (approval_status IN ('PENDING', 'APPROVED', 'BLOCKED'));

CREATE UNIQUE INDEX IF NOT EXISTS users_email_lower_unique
    ON public.users (LOWER(email));

CREATE INDEX IF NOT EXISTS users_approval_status_idx
    ON public.users (approval_status);

CREATE INDEX IF NOT EXISTS users_verification_token_hash_idx
    ON public.users (verification_token_hash)
    WHERE verification_token_hash IS NOT NULL;

CREATE INDEX IF NOT EXISTS users_reset_token_hash_idx
    ON public.users (reset_token_hash)
    WHERE reset_token_hash IS NOT NULL;

-- Authentication data must never be accessible through the public API.
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.users FROM anon, authenticated;

-- Signals remain publicly readable by the app, but writes are backend-only.
DROP POLICY IF EXISTS "Allow public insert access" ON public.signals;
REVOKE INSERT, UPDATE, DELETE ON TABLE public.signals
    FROM anon, authenticated;

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS users_set_updated_at ON public.users;
CREATE TRIGGER users_set_updated_at
BEFORE UPDATE ON public.users
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at();

COMMIT;
