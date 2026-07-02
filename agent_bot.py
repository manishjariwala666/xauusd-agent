import os
import telebot
from telebot import types

# GitHub Secrets se token utha raha hai
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

# /start command handle karne ke liye
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Manissh bhai, XAUUSD Agent Online hai! Main aapke commands ke liye taiyar hoon.")

# /update_legal command handle karne ke liye
@bot.message_handler(commands=['update_legal'])
def handle_update(message):
    bot.reply_to(message, "Update process trigger ho gaya hai... Database sync ho raha hai.")
    # Yahan aap apna logic call kar sakte hain jo data fetch karega
    
# Bot ko chalaye rakhne ke liye (Long Polling)
if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()
