import os
import logging
from anthropic import Anthropic
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(**name**)

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
histories = {}

def start(update: Update, context: CallbackContext):
histories[update.effective_user.id] = []
update.message.reply_text(
“👋 Привет! Я ИИ помощник на базе Claude.\n\n”
“/start — начать заново\n”
“/clear — очистить историю”
)

def clear(update: Update, context: CallbackContext):
histories[update.effective_user.id] = []
update.message.reply_text(“🧹 История очищена!”)

def handle(update: Update, context: CallbackContext):
user_id = update.effective_user.id
text = update.message.text

```
if user_id not in histories:
    histories[user_id] = []

histories[user_id].append({"role": "user", "content": text})

if len(histories[user_id]) > 20:
    histories[user_id] = histories[user_id][-20:]

try:
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=histories[user_id]
    )
    reply = response.content[0].text
    histories[user_id].append({"role": "assistant", "content": reply})
    update.message.reply_text(reply)
except Exception as e:
    logger.error(f"Error: {e}")
    update.message.reply_text("⚠️ Ошибка, попробуйте снова.")
```

def main():
token = os.environ[“TELEGRAM_BOT_TOKEN”]
updater = Updater(token)
dp = updater.dispatcher
dp.add_handler(CommandHandler(“start”, start))
dp.add_handler(CommandHandler(“clear”, clear))
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle))
logger.info(“Bot started!”)
updater.start_polling()
updater.idle()

if **name** == “**main**”:
main()
