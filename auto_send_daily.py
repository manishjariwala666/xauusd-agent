import os
from datetime import datetime
from config import get_settings
from services.telegram_service import TelegramService
from services.twelve_data_multi_tf import fetch_multi_tf_high_low

def send_auto_vip():
    print("Fetching today's market data...")
    try:
        data = fetch_multi_tf_high_low()
    except Exception as e:
        print(f"❌ Data fetch error: {e}")
        return
        
    daily = next((item for item in data if item["Timeframe"] == "Daily"), None)
    if not daily:
        print("❌ Error: Daily data not found.")
        return

    high = daily["High"]
    low = daily["Low"]
    
    # Auto-calculation logic based on your 0.25 multiplier pattern
    step_range = high - low
    step = step_range * 0.25
    buy_base = low + step
    sell_base = high - step

    msg = f"""📊 <b>XAUUSD DAILY MARKET LEVELS</b> 📊
🗓️ Date: {datetime.now().strftime('%Y-%m-%d')} (Friday)

🌅 <b>MORNING SESSION SETUP</b>
📈 <b>BUY BASE:</b> {buy_base:.2f}
🎯 Buy Targets: {buy_base + step:.2f} | {buy_base + (step*2):.2f} | {buy_base + (step*3):.2f} | {buy_base + (step*4):.2f}

📉 <b>SELL BASE:</b> {sell_base:.2f}
🎯 Sell Targets: {sell_base - step:.2f} | {sell_base - (step*2):.2f} | {sell_base - (step*3):.2f} | {sell_base - (step*4):.2f}

⚠️ Manage risk carefully. This is market analysis, not guaranteed financial advice.
— VenusRealm"""

    print("\nDrafted Message:\n" + msg + "\n")
    print("Sending message to Telegram VIP Channel...")
    try:
        tg = TelegramService()
        settings = get_settings()
        if not settings.telegram_chat_id:
            raise ValueError("TELEGRAM_CHAT_ID is missing in .env")
            
        tg.send_text(settings.telegram_chat_id, msg)
        print("✅ SUCCESS: 100% Auto VIP Message sent to Telegram!")
    except Exception as e:
        print(f"❌ Telegram send failed: {e}")

if __name__ == "__main__":
    send_auto_vip()
