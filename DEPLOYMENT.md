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
| `APP_BASE_URL` | Verification/reset links and public SEO URLs | Public Streamlit website URL. |
| `BACKEND_BASE_URL` | Telegram webhook registration | Railway-generated HTTPS domain for the FastAPI service. |
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

Create two Railway services from the same GitHub repository:

1. **API service**: use `/railway.toml` (the default config). Generate a
   public domain, then set that exact HTTPS URL as `BACKEND_BASE_URL`.
2. **Worker service**: set its Config File Path to
   `/railway.worker.toml`. It must not have a public domain or healthcheck.

Copy the same core Supabase/JWT variables to both services. Put webhook
variables on the API service and agent/provider/channel variables on the
worker. Variables can be shared in Railway to prevent drift.

The API `/health` endpoint verifies database connectivity. Railway injects
`PORT`, and the API start command binds to it. Both services use Railpack,
install `requirements.txt`, restart on failure, and run the idempotent
database migrations before processing work.

## Deployment checklist

- Rotate any credential that has ever appeared in source, chat, screenshots,
  logs, or commit history.
- Confirm `DATABASE_URL`, `SUPABASE_URL`, and `SUPABASE_KEY` belong to the
  same Supabase project.
- Configure all startup-required values on Streamlit and both Railway services.
- Configure SMTP and set `APP_BASE_URL` to the Streamlit URL.
- Generate the Railway API domain and set `BACKEND_BASE_URL`.
- Configure Telegram, add the bot to the target channel, and redeploy API.
- Configure Meta webhook URL as `/webhooks/whatsapp` on the Railway API domain.
- Configure the AI provider, image provider, and Google service-account JSON.
- Configure payment and verified-member invite settings.
- Deploy API with `/railway.toml`; verify `/health` returns HTTP 200.
- Deploy worker with `/railway.worker.toml`; confirm heartbeats and queue runs.
- Run `python test_connection.py` in the deployment shell.
- Test registration email, login, payment gating, one signal, Telegram reply,
  WhatsApp reply, blog/image generation, and human takeover.
- Confirm normal users cannot access the Admin or AI Agents interfaces.
