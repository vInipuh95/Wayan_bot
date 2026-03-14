import os
import logging
from collections import defaultdict
import anthropic as anthropic_module
from telegram import Update, MessageEntity
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

client = anthropic_module.Anthropic(api_key=ANTHROPIC_API_KEY)

conversation_histories: dict[int, list[dict]] = defaultdict(list)

SYSTEM_PROMPT = (
    "You are a helpful AI assistant powered by Anthropic Claude. "
    "Be concise, clear, and friendly in your responses."
)

GROUP_CHAT_TYPES = {"group", "supergroup"}


def is_group_chat(update: Update) -> bool:
    return update.effective_chat.type in GROUP_CHAT_TYPES


def bot_is_mentioned(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    message = update.message
    if not message or not message.entities:
        return False
    bot_username = context.bot.username
    for entity in message.entities:
        if entity.type == MessageEntity.MENTION:
            mention_text = message.text[entity.offset : entity.offset + entity.length]
            if mention_text.lstrip("@").lower() == bot_username.lower():
                return True
    return False


def is_reply_to_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    message = update.message
    if not message or not message.reply_to_message:
        return False
    return message.reply_to_message.from_user.id == context.bot.id


def get_history_key(update: Update) -> int:
    if is_group_chat(update):
        return update.effective_chat.id
    return update.effective_user.id


def strip_bot_mention(text: str, bot_username: str) -> str:
    mention = f"@{bot_username}"
    return text.replace(mention, "").strip()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    key = get_history_key(update)
    conversation_histories[key].clear()
    user = update.effective_user
    await update.message.reply_text(
        f"Hello {user.first_name}! I'm an AI assistant powered by Claude.\n\n"
        "Commands:\n"
        "/start — Start a new conversation\n"
        "/clear — Clear conversation history"
    )


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    key = get_history_key(update)
    conversation_histories[key].clear()
    await update.message.reply_text("Conversation history cleared!")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if is_group_chat(update):
        if not bot_is_mentioned(update, context) and not is_reply_to_bot(update, context):
            return

    user_text = update.message.text
    if is_group_chat(update) and context.bot.username:
        user_text = strip_bot_mention(user_text, context.bot.username)

    if not user_text:
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    key = get_history_key(update)
    history = conversation_histories[key]
    history.append({"role": "user", "content": user_text})

    if len(history) > 40:
        history[:] = history[-40:]

    try:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=history,
        )

        assistant_reply = response.content[0].text
        history.append({"role": "assistant", "content": assistant_reply})
        await update.message.reply_text(assistant_reply)

    except Exception as e:
        logger.error("Error calling Anthropic API: %s", e)
        history.pop()
        await update.message.reply_text("Sorry, I encountered an error. Please try again.")


def main() -> None:
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
