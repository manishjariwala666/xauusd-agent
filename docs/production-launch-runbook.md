# VenusRealm Production Launch Runbook

This runbook is a manual safety checklist. It does not authorize a deployment,
database migration, DNS change, or credential change. Replace placeholders only
inside an approved deployment session and never commit their values.

## 1. Pre-launch checks

- [ ] Confirm the approved release branch and commit SHA with `git branch --show-current`
  and `git rev-parse HEAD`.
- [ ] Confirm `git status --short` is empty.
- [ ] Confirm the release has passed an isolated PostgreSQL migration rehearsal.
- [ ] Assign a launch owner, database backup owner, rollback owner, and final
  go/no-go decision owner.
- [ ] Record the rollback decision time. Stop if health, readiness, migrations,
  authentication, or public routes fail before that point.
- [ ] Confirm a fresh production database backup exists and has been verified.
- [ ] Confirm the previous Railway deployments and the existing Streamlit/Railway
  site remain available as rollback paths.
- [ ] Keep `BLOCK_SEARCH_INDEXING=true` until the public site, canonical URLs,
  robots rules, sitemap, and content pages have been approved. Change it to
  `false` only as a separate, explicit launch decision.

### Environment variable checklist

Confirm presence and ownership without printing values:

- [ ] `DATABASE_URL`
- [ ] `JWT_SECRET` and `JWT_ISSUER`
- [ ] `ADMIN_BFF_SHARED_SECRET`
- [ ] `APP_BASE_URL`, `PUBLIC_WEBSITE_URL`, `BACKEND_BASE_URL`, `PUBLIC_API_URL`
- [ ] `SUPABASE_URL` and the correct least-privileged Supabase key
- [ ] Telegram and WhatsApp configuration, only when those channels are approved
- [ ] Google service-account and Sheet configuration, only when Sheet sync is approved
- [ ] AI-provider configuration, only for approved agents
- [ ] `BLOCK_SEARCH_INDEXING`

Never paste environment values into tickets, logs, screenshots, shell history,
or this repository.

## 2. PostgreSQL backup procedure

Use an access-controlled directory on the launch operator's workstation. The
following commands contain placeholders only:

```bash
test -n "${PRODUCTION_DATABASE_URL:-}"
export BACKUP_DIR="/secure/path/to/venusrealm-backup"
mkdir -p "$BACKUP_DIR"

pg_dump \
  --dbname="$PRODUCTION_DATABASE_URL" \
  --format=custom \
  --no-owner \
  --no-privileges \
  --file="$BACKUP_DIR/venusrealm-prelaunch.dump"

pg_dump \
  --dbname="$PRODUCTION_DATABASE_URL" \
  --schema-only \
  --no-owner \
  --no-privileges \
  --file="$BACKUP_DIR/venusrealm-prelaunch-schema.sql"

psql "$PRODUCTION_DATABASE_URL" --csv \
  --command="SELECT name, applied_at FROM public.schema_migrations ORDER BY applied_at, name" \
  > "$BACKUP_DIR/schema-migrations.csv"

pg_restore --list "$BACKUP_DIR/venusrealm-prelaunch.dump" > /dev/null
BACKUP_FILE="$BACKUP_DIR/venusrealm-prelaunch.dump" scripts/verify_backup.sh
```

Record file size, creation time, checksum, PostgreSQL client version, and the
operator who verified the archive. Store the backup separately from the deploy
environment.

## 3. Migration procedure

1. Announce the maintenance window. Consider read-only mode when writes could
   race with schema changes.
2. Take and verify all backups before changing application or database state.
3. Confirm the rollback owner and previous Railway deployment IDs.
4. Deploy the approved backend code while keeping public traffic controlled.
5. Run the approved migration entrypoint exactly once. Do not run individual SQL
   files manually unless the incident owner explicitly approves it.
6. Verify `public.schema_migrations` contains exactly the expected approved
   records and includes `020_automation_service_leads.sql`.
7. Run the readiness helper without printing configuration:

   ```bash
   DATABASE_URL="$PRODUCTION_DATABASE_URL" scripts/verify_launch_readiness.py
   ```

8. Verify `/health` returns HTTP 200.
9. Verify `/ready` returns HTTP 200 and reports database and schema readiness.
10. Inspect sanitized backend and worker logs. Stop on the first migration,
    readiness, authentication, or repeated worker error.

Do not continue to the public-site launch while the backend is degraded.

## 4. Rollback procedure

### Application rollback

1. Stop the launch and prevent additional writes where operationally safe.
2. Roll back API, worker, and web to their recorded previous Railway deployment.
3. Confirm the previous application version is compatible with the current
   database before reopening traffic.
4. Recheck health, readiness, authentication, and worker stability.

### Database rollback decision

Database rollback is required when the migrated schema corrupts data, prevents
the previous application from operating, or cannot be safely forward-fixed
inside the approved incident window. A verified `pg_dump` restoration is the
safest full rollback option.

Available targeted rollback files:

- `migrations/014_admin_auth_foundation.rollback.sql`
- `migrations/015_admin_content_cms.rollback.sql`
- `migrations/016_admin_media_library.rollback.sql`
- `migrations/rollback/017_admin_seo_management.rollback.sql`
- `migrations/018_signals_admin.rollback.sql`
- `migrations/019_announcements_verified_results.rollback.sql`
- `migrations/020_automation_service_leads.rollback.sql`

**Warning:** rollback SQL may drop tables, columns, indexes, constraints, or
data. Never auto-run rollback files. Review dependencies and preserve an
incident copy of database logs, migration records, deployment logs, and error
evidence before any rollback.

For a full restore, create a new empty recovery database first, validate the
archive there, and switch only after approval. Example placeholders:

```bash
pg_restore --list "/secure/path/to/venusrealm-prelaunch.dump" > /dev/null
pg_restore \
  --dbname="$RECOVERY_DATABASE_URL" \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges \
  "/secure/path/to/venusrealm-prelaunch.dump"
```

## 5. Netlify and DNS launch order

1. Make the backend healthy and ready first.
2. Deploy the approved public application to Netlify production second.
3. Smoke-test the Netlify URL before changing any DNS record.
4. Change DNS last, after the backend and frontend checks pass.
5. Keep the prior Streamlit/Railway site and deployment IDs available until the
   rollback window closes.

Do not delete old services, DNS records, backups, or deployment history during
the launch window.

## 6. Post-launch smoke tests

- [ ] Homepage
- [ ] `/blog` and one real article
- [ ] `/signals`
- [ ] `/announcements`
- [ ] `/results`
- [ ] `/automation-services` and its lead form
- [ ] Admin login and protected-route enforcement
- [ ] API `/health`
- [ ] API `/ready`
- [ ] `robots.txt`, sitemap, canonical URLs, and indexing decision
- [ ] Light and dark themes on desktop and mobile
- [ ] No blank pages or horizontal overflow
- [ ] No secret values in HTML, browser bundles, API responses, or logs
- [ ] No unexpected Telegram, WhatsApp, AI-agent, scheduler, or publishing action

## 7. Credential rotation checklist

Rotate and verify these credential categories through their owning providers:

- [ ] Database credentials
- [ ] JWT and admin/BFF secrets
- [ ] Telegram bot and webhook tokens
- [ ] Google service-account credentials
- [ ] Supabase keys
- [ ] Any other credential category present in the earlier audit ZIP

After rotation, invalidate the previous credential, update only approved secret
stores, redeploy affected services in dependency order, and verify sanitized
logs. Never commit rotated values.
