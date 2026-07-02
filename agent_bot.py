import os
import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Token setup
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

# Google Sheet setup function
def sync_data():
    scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets', "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('semiotic-garden-473909-k5-12652fc38a39.json', scope)
    client = gspread.authorize(creds)
    # Sheet open kar raha hai
    sheet = client.open("xauusd_automation").worksheet("Sheet1")
    return sheet.get_all_values()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Manissh bhai, XAUUSD Agent Online hai! Main aapke commands ke liye taiyar hoon.")

@bot.message_handler(commands=['update_legal'])
def handle_update(message):
    bot.reply_to(message, "Update process trigger ho gaya hai... Database sync ho raha hai.")
    try:
        data = sync_data()
        bot.reply_to(message, "Sync Complete! Database update ho gaya hai.")
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")

if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()
