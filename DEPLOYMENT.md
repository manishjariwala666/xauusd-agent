# Production deployment

The Streamlit website and FastAPI backend share one Supabase project. Never
commit environment values. Configure them in Streamlit Secrets and Railway
Variables.

## Startup-required variables

These four values are validated by every process at startup:

| Variable | Source |
|---|---|
| `DATABASE_URL` | Supabase Database settings, preferably the session-pooler connection string. It must point to the same project as `SUPABASE_URL`. |
| `SUPABASE_URL` | Supabase Project Settings > API. |
| `SUPABASE_KEY` | Supabase server-side service-role/secret key. Never use it in browser code. |
| `JWT_SECRET` | A private cryptographically random value of at least 32 characters, generated outside the repository. |

## Website authentication and email

| Variable | Required for | Source/default |
|---|---|---|
| `APP_BASE_URL` | Verification/reset links and public SEO URLs | Public Streamlit website URL. Final value: `https://venusrealm.net`. |
| `BACKEND_BASE_URL` | Telegram webhook registration | Public FastAPI URL. Final value: `https://api.venusrealm.net`. |
| `PUBLIC_WEBSITE_URL` | Canonical website/blog links | Optional override for public website links. Final value: `https://venusrealm.net`. |
| `PUBLIC_API_URL` | Telegram webhook URL base | Optional override for API/webhook links. Final value: `https://api.venusrealm.net`; keep the Railway fallback URL working. |
| `BLOCK_SEARCH_INDEXING` | Temporary launch/migration crawl lock | Set `true` while moving to `https://venusrealm.net`; set `false` only after the public site is ready for Google. |
| `JWT_ISSUER` | JWT validation | Optional; defaults to `ai-market-analytics-pro`. |
| `JWT_TTL_MINUTES` | JWT lifetime | Optional; defaults to `60`. |
| `SMTP_HOST` | Email verification and password reset | Transactional email provider. |
| `SMTP_PORT` | Email verification and password reset | Email provider; defaults to `587`. |
| `SMTP_USERNAME` | Email verification and password reset | Email provider. |
| `SMTP_PASSWORD` | Email verification and password reset | Email provider/API SMTP credential. |
| `EMAIL_FROM` | Email verification and password reset | Verified sender at the email provider. |
| `SMTP_USE_TLS` | SMTP transport security | Optional; defaults to `true`. |

`APP_BASE_URL`, `SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and
`EMAIL_FROM` are operationally mandatory for user registration, verification,
and forgot-password flows even though the process can start without them.

For the `venusrealm.net` migration, the existing GoDaddy/Airo website may be
replaced, but email DNS must remain untouched. The root domain and `www` must
point to the Streamlit website service, not the FastAPI API service. Keep
`BLOCK_SEARCH_INDEXING=true` on the website/API until DNS, SSL, homepage, blog
URLs, admin login, sitemap, and Telegram links are verified. Then switch it to
`false` and regenerate/publish SEO files.

## Telegram

| Variable | Required for | Source |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Signals, replies, announcements, webhook | Telegram BotFather. |
| `TELEGRAM_CHAT_ID` | Signal/announcement destination | Telegram channel ID/username; add the bot as an administrator. |
| `TELEGRAM_WEBHOOK_SECRET` | Authenticated inbound webhook | Generate a private random value. |
| `TELEGRAM_INVITE_URL` | Verified-user premium link | Private channel invite link managed by the business. |
| `PROFIT_PROOF_TELEGRAM_URL` | Profit-proof CTA | Dedicated Telegram link managed by the business. |

## WhatsApp Business

| Variable | Required for | Source |
|---|---|---|
| `WHATSAPP_ACCESS_TOKEN` | Replies, signals, broadcasts | Meta for Developers > WhatsApp > permanent system-user token. |
| `WHATSAPP_PHONE_NUMBER_ID` | Cloud API sender | Meta WhatsApp API Setup. |
| `WHATSAPP_BUSINESS_ACCOUNT_ID` | Business account identity | Meta WhatsApp API Setup. |
| `WHATSAPP_VERIFY_TOKEN` | Meta webhook verification | Generate a private random value and enter the same value in Meta. |
| `META_APP_SECRET` | Webhook signature validation | Meta App Settings > Basic. |
| `SUPPORT_WHATSAPP_URL` | Verified-user premium/support link | Business-managed WhatsApp URL. |

## AI, Google Sheets, and market data

| Variable | Required for | Source/default |
|---|---|---|
| `AI_PROVIDER` | Text generation provider | `GEMINI` or `OPENAI`; defaults to `GEMINI`. |
| `GEMINI_API_KEY` | Gemini text agents | Google AI Studio/Google Cloud. Required when `AI_PROVIDER=GEMINI`. |
| `OPENAI_API_KEY` | OpenAI text and all image generation | OpenAI project API key. Required for Image Agent. |
| `AI_TEXT_MODEL` | Text model selection | Optional provider model ID; current default is in `config.py`. |
| `AI_IMAGE_MODEL` | Image model selection | Optional OpenAI image model ID; current default is in `config.py`. |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Google Sheets Signal Agent input | Complete one-line Google Cloud service-account JSON. Share the sheet with its `client_email`. |
| `GOOGLE_SHEET_NAME` | Signal worksheet | Optional; defaults to `xauusd_automation`. |
| `GOOGLE_WORKSHEET_NAME` | Signal tab | Optional; defaults to `Sheet1`. |
| `GOLDAPI_KEY` | Exact XAU/USD spot quote | GoldAPI; optional because Yahoo is the fallback. |
| `XAUUSD_SYMBOL` | Yahoo fallback instrument | Optional; defaults to `GC=F`. |
| `SIGNAL_POLL_SECONDS` | Legacy signal polling interval | Optional; minimum `10`, default `60`. |

## Subscription, branding, and worker tuning

| Variable | Required for | Source/default |
|---|---|---|
| `USDT_WALLET_ADDRESS` | Payment instructions | Business-controlled wallet. |
| `USDT_NETWORK` | Payment instructions | Network accepted by that wallet. |
| `SUBSCRIPTION_PRICE_USDT` | Checkout price | Business pricing decision. |
| `SUPPORT_EMAIL` | Public support contact | Business mailbox. |
| `BRAND_NAME` | Public branding/watermark | Optional; defaults to `AI Market Analytics Pro`. |
| `HUMAN_TAKEOVER_MINUTES` | AI reply pause after admin response | Optional; defaults to `30`. |
| `WORKER_POLL_SECONDS` | Queue polling | Optional; minimum `1`, default `5`. |
| `TEST_GOOGLE_CREDENTIALS` | Local pre-flight only | Optional boolean used by `test_connection.py`. |
| `PORT` | FastAPI bind port | Injected automatically by Railway; do not set manually. |

The payment wallet, network, and price are operationally required before
accepting customer payments.

## Railway services

Create three Railway services from the same GitHub repository:

1. **Website service `xauusd-agent-web`**: set Config File Path to
   `/railway.web.toml`. It runs:
   `streamlit run app.py --server.address 0.0.0.0 --server.port $PORT --server.headless true`.
   Healthcheck path: `/_stcore/health` (verified locally; do not use FastAPI
   `/health` for this service). Attach `venusrealm.net` and `www.venusrealm.net`
   only to this service.
2. **API service `xauusd-agent-api`**: use `/railway.toml` (the default config).
   It runs: `uvicorn backend:app --host 0.0.0.0 --port $PORT`. Attach
   `api.venusrealm.net` only to this service. The old Railway URL
   `https://xauusd-agent-api-production.up.railway.app` must remain working.
3. **Worker service `xauusd-agent-worker`**: set Config File Path to
   `/railway.worker.toml`. It must not have a public custom domain or
   healthcheck.

Copy the same core Supabase/JWT variables to all three services because the
website needs database access for login, admin, public content, blog gallery,
view analytics, and payment gating. Put webhook variables on the API service
and agent/provider/channel variables on the worker. Variables can be shared in
Railway to prevent drift. The website service may apply idempotent migrations
when it imports database-backed modules; this is safe because migrations are
tracked in `schema_migrations`, but the API service remains the primary
startup migration runner.

The API `/health` endpoint is lightweight liveness and `/ready` verifies
database connectivity. Railway injects `PORT`, and each start command binds to
it. All services use Railpack, install `requirements.txt`, and restart on
failure.

## Domain mapping

| Domain | Railway service | Purpose |
|---|---|---|
| `venusrealm.net` | `xauusd-agent-web` | Canonical Streamlit public website/admin UI. |
| `www.venusrealm.net` | `xauusd-agent-web` | Website alias; prefer redirecting to `venusrealm.net`. |
| `api.venusrealm.net` | `xauusd-agent-api` | FastAPI health, readiness, Telegram, WhatsApp, and webhooks. |
| none | `xauusd-agent-worker` | Background jobs only; no public domain. |

Do not attach `venusrealm.net` or `www.venusrealm.net` to
`xauusd-agent-api`, otherwise visitors will see the FastAPI backend instead of
the Streamlit homepage/blog/admin UI.

Preferred canonical URL is `https://venusrealm.net`. The safest `www` behavior
is a permanent redirect to the root domain. If Railway provides a primary-domain
or redirect option for custom domains, use it there. If not, use a lightweight
redirect service or GoDaddy forwarding for `www` only after confirming it does
not interfere with Railway SSL. If GoDaddy cannot point the apex/root domain
using the exact Railway-required record, fallback plan is:

1. Connect `www.venusrealm.net` to `xauusd-agent-web`.
2. Permanently redirect `venusrealm.net` to `https://www.venusrealm.net`.
3. Temporarily set `PUBLIC_WEBSITE_URL=https://www.venusrealm.net` until apex
   support is available.

Do not switch canonical away from `https://venusrealm.net` unless apex DNS is
technically blocked.

## GoDaddy DNS checklist

Do not guess DNS targets. First add each custom domain in Railway and copy the
exact records from Railway service Settings > Networking > Custom Domain.

Use this table format for every Railway-provided record:

| Domain | Railway service | Record Type | Host/Name | Value/Target | TTL | Purpose |
|---|---|---|---|---|---|---|
| `venusrealm.net` | `xauusd-agent-web` | Copy from Railway | Copy from Railway | Copy from Railway | 600 or 1 hour | Root website domain. |
| `www.venusrealm.net` | `xauusd-agent-web` | Copy from Railway | Copy from Railway | Copy from Railway | 600 or 1 hour | Website alias / redirect source. |
| `api.venusrealm.net` | `xauusd-agent-api` | Copy from Railway | Copy from Railway | Copy from Railway | 600 or 1 hour | API and webhook domain. |

If Railway requires TXT verification, add each TXT record separately with the
exact Host/Name and Value/Target Railway shows.

Before changing GoDaddy DNS, check for conflicts:

- `@` A record
- `@` AAAA record
- `@` CNAME/ALIAS record
- `www` CNAME/A/AAAA record
- `api` CNAME/A/AAAA record
- forwarding configuration for root or `www`

The old GoDaddy/Airo website may be disconnected because it is unused. Do not
remove or modify MX, SPF, DKIM, DMARC, email-verification TXT records, or
nameservers unless separately approved.

## Telegram webhook migration

Master Telegram webhook belongs to `xauusd-agent-api`.

Final intended Master AI webhook URL:
`https://api.venusrealm.net/webhooks/telegram/master`

Safe migration order:

1. Add `api.venusrealm.net` to Railway `xauusd-agent-api`.
2. Add exact Railway DNS/TXT records in GoDaddy.
3. Wait for Railway SSL active.
4. Verify `https://api.venusrealm.net/health` returns 200.
5. Verify `https://api.venusrealm.net/ready` returns 200.
6. Set API service variables:
   `PUBLIC_API_URL=https://api.venusrealm.net` and
   `BACKEND_BASE_URL=https://api.venusrealm.net`.
7. Redeploy API so startup registers Telegram webhooks to the API domain.
8. Test `/master status`.

Rollback: set `PUBLIC_API_URL` and `BACKEND_BASE_URL` back to the Railway API
fallback URL, redeploy API, and keep the previous webhook URL until
`api.venusrealm.net` is healthy. Do not weaken `TELEGRAM_WEBHOOK_SECRET`,
admin authorization, dedupe protection, or public command safety rules.

## Deployment checklist

- Rotate any credential that has ever appeared in source, chat, screenshots,
  logs, or commit history.
- Confirm `DATABASE_URL`, `SUPABASE_URL`, and `SUPABASE_KEY` belong to the
  same Supabase project.
- Configure all startup-required values on website, API, and worker services.
- Configure SMTP and set website variables:
  `PUBLIC_WEBSITE_URL=https://venusrealm.net`,
  `APP_BASE_URL=https://venusrealm.net`, and
  `BLOCK_SEARCH_INDEXING=true` until final QA is complete.
- Configure API variables:
  `PUBLIC_API_URL=https://api.venusrealm.net`,
  `BACKEND_BASE_URL=https://api.venusrealm.net`, and
  `BLOCK_SEARCH_INDEXING=true` until final QA is complete.
- Configure Telegram, add the bot to the target channel, and redeploy API.
- Configure Meta webhook URL as `/webhooks/whatsapp` on the Railway API domain.
- Configure the AI provider, image provider, and Google service-account JSON.
- Configure payment and verified-member invite settings.
- Deploy website with `/railway.web.toml`; verify `/_stcore/health` returns HTTP 200.
- Deploy API with `/railway.toml`; verify `/health` returns HTTP 200.
- Deploy worker with `/railway.worker.toml`; confirm heartbeats and queue runs.
- Run `python test_connection.py` in the deployment shell.
- Test registration email, login, payment gating, one signal, Telegram reply,
  WhatsApp reply, blog/image generation, and human takeover.
- Confirm normal users cannot access the Admin or AI Agents interfaces.
- After production checks pass, set `BLOCK_SEARCH_INDEXING=false` on website
  and API, regenerate SEO files, and verify `robots.txt` allows the sitemap.
