from datetime import datetime
from config import get_settings
from services.telegram_service import TelegramService

def send_scheduled_profit():
    # Abhi hum basic structure set kar rahe hain taaki timer (cron) kaam karne lage.
    # Next step mein hum isme aapki Google Sheet (MasterPivot) ko read karne ka exact function link kar denge.
    
    now = datetime.now()
    session_name = "Morning Session" if now.hour < 18 else "Evening Session"
    
    # Demo ke liye aaj ke numbers. Ise hum MasterPivot se link karenge.
    entry = 4391.00
    target_hit = 4350.00
    points = abs(entry - target_hit)
    dollar_profit = points * 10
    
    msg = (
        f"🎯 Yahooo VenusRealm TARGET HIT ✅\n\n"
        f"XAUUSD\n"
        f"Time: {now.strftime('%d %b %Y')} · {session_name}\n"
        f"📉 Base (Entry): {entry:.2f}\n"
        f"🎯 Target Hit: {target_hit:.2f}\n\n"
        f"Profit: +{points:.2f} points 🟢\n"
        f"💵 Profit on 0.10 Lot: ${dollar_profit:.2f} 💰 PROFIT BOOK ✅\n\n"
        f"🎉 Enjoy your profit & have a great day!\n"
        f"— VenusRealm"
    )
    
    try:
        tg = TelegramService()
        settings = get_settings()
        tg.send_text(settings.telegram_chat_id, msg)
        print(f"✅ SUCCESS: {session_name} Profit message sent!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    send_scheduled_profit()
