# bot.py
import logging
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

# Загружаем переменные окружения (BOT_TOKEN, BACKEND_URL)
load_dotenv()

# --- Настройки ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
# URL вашего Django-приложения. Должен быть HTTPS.
BACKEND_URL = os.getenv("BACKEND_URL")
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Отправляет сообщение с кнопкой для запуска Web App.
    """
    user = update.effective_user
    logger.info(f"User {user.username} ({user.id}) started the bot.")

    # Создаем кнопку, которая открывает ваше веб-приложение
    keyboard = [
        [InlineKeyboardButton(
            "🚀 Открыть приложение TradeHub",
            web_app=WebAppInfo(url=BACKEND_URL)
        )]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👋 Добро пожаловать в TradeHub!\n\nНажмите кнопку ниже, чтобы запустить приложение.",
        reply_markup=reply_markup
    )

def main():
    """Основная функция запуска бота."""
    if not BOT_TOKEN or not BACKEND_URL:
        logger.error("BOT_TOKEN и BACKEND_URL должны быть установлены в .env файле!")
        return

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    logger.info("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()