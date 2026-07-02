import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials

TOKEN = "8514838628:AAE1q7YOxsEzObeVXxNE63efpE0qDy3-Iyk"
bot = telebot.TeleBot(TOKEN)

def sync_data():
    scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets', "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open("xauusd_automation").worksheet("Sheet1")
    
    # Sirf wahi data uthaye jahan time maujood hai
    all_data = sheet.get_all_values()
    valid_data = [row for row in all_data if row[0] and "AM" in row[0] or "PM" in row[0]]
    
    return valid_data

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Manissh bhai, XAUUSD Agent Online hai!")

@bot.message_handler(commands=['update_legal'])
def handle_update(message):
    bot.reply_to(message, "Database sync ho raha hai...")
    try:
        data = sync_data()
        bot.reply_to(message, f"Sync Complete! {len(data)} rows processed.")
        @bot.message_handler(commands=['clear'])
def clear_chat(message):
    # Yeh loop 100 messages tak delete karne ki koshish karega
    for i in range(message.message_id, message.message_id - 100, -1):
        try:
            bot.delete_message(message.chat.id, i)
        except:
            continue
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")

if __name__ == "__main__":
    bot.infinity_polling()
