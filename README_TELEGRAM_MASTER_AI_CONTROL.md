# Telegram Master AI Control

This patch adds an isolated Telegram command controller for the Master AI orchestrator.
It does not replace the existing Telegram reply agent. To enable routing, call
`try_handle_telegram_update()` at the beginning of the existing Telegram webhook
handler and return early when `handled=True`.

Example integration shape:

```python
from services.telegram_master_ai_control import try_handle_telegram_update

result = try_handle_telegram_update(
    update,
    sender=lambda chat_id, text: TelegramService().send_message(chat_id, text),
    supabase=supabase,
)
if result.handled:
    return {"ok": True, "master_ai": True}
```

The handler authorizes only Telegram user IDs listed in one of these environment
variables or equivalent settings fields:

- `TELEGRAM_ADMIN_USER_ID`
- `TELEGRAM_ADMIN_USER_IDS`
- `MASTER_AI_TELEGRAM_ADMIN_USER_ID`
- `MASTER_AI_TELEGRAM_ADMIN_USER_IDS`

Do not commit `.env`, `service_account.json`, Telegram tokens, Supabase secrets,
or Railway credentials.

Supported commands:

- `/master status`
- `/master run daily_content`
- `/master run signal`
- `/master run blog`
- `/master run image`
- `/master help`

All user-facing service failures return exactly:

```text
⚠️ Service temporarily unavailable. Please try again later.
```
