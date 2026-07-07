# Two Telegram Bots: Signal Bot and Master AI Admin Bot

This update separates public signal/reply Telegram behavior from private Master AI admin control.

## Environment variables

Do not rename or reuse existing secrets.

- `TELEGRAM_BOT_TOKEN`: existing Buy/Sell Signal Bot only.
- `MASTER_AI_TELEGRAM_BOT_TOKEN`: new Master AI Admin Bot only.
- `TELEGRAM_ADMIN_USER_ID`: Telegram user ID authorized to use `/master` commands.
- Optional: `TELEGRAM_ADMIN_USER_IDS` for comma-separated additional admin IDs.

Never commit `.env`, `service_account.json`, Railway variables, Supabase keys, or Telegram tokens.

## Webhook endpoints

Keep both endpoints separate:

- `/webhooks/telegram`: existing signal/reply bot webhook using `TELEGRAM_BOT_TOKEN`.
- `/webhooks/telegram/master`: new Master AI admin bot webhook using `MASTER_AI_TELEGRAM_BOT_TOKEN`.

## Backend integration

If `backend.py` is FastAPI-based, register the optional router:

```python
from services.telegram_master_ai_webhook import router as telegram_master_ai_router

if telegram_master_ai_router is not None:
    app.include_router(telegram_master_ai_router)
```

At the very beginning of the existing `/webhooks/telegram` handler, add the guard:

```python
from services.telegram_master_ai_webhook import handle_signal_telegram_master_command_guard

ignored = handle_signal_telegram_master_command_guard(update)
if ignored is not None:
    return ignored
```

This ensures the public Buy/Sell Signal Bot never responds to `/master` commands.

## Master AI bot behavior

The Master AI bot handles only:

- `/master status`
- `/master run daily_content`
- `/master run signal`
- `/master run blog`
- `/master run image`
- `/master help`

Non-`/master` messages sent to the Master AI bot are silently ignored and never routed to public buy/sell signal logic.

All user-facing service failures return exactly:

```text
⚠️ Service temporarily unavailable. Please try again later.
```
