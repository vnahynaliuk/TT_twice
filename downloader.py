"""
Telegram Bot для завантаження відео
Завантажує відео з TikTok, Instagram Reels, YouTube та Twitter/X
"""

import logging
import os
from dotenv import load_dotenv
from telegram import BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from cleanup import cleanup_old_downloads
from handlers import start, help_command, about, cleanup, vlop_handler, download_video

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main() -> None:
    cleanup_old_downloads()
    logger.info("Очищення старих файлів завершено при старті бота")

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN не знайдено в файлі .env")

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start_pohnaly", start))
    application.add_handler(CommandHandler("help_me_please", help_command))
    application.add_handler(CommandHandler("who_asked", about))
    application.add_handler(CommandHandler("cleanup", cleanup))

    async def set_commands(app):
        commands = [
            BotCommand("start_pohnaly", "Привіт"),
            BotCommand("help_me_please", "Показати цю довідку"),
            BotCommand("who_asked", "Про цього бота"),
            BotCommand("cleanup", "Очистити старі файли"),
        ]
        await app.bot.set_my_commands(commands)
        logger.info("Команди встановлені в Telegram")

    application.post_init = set_commands

    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(vlop|влоп)'), vlop_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))

    logger.info("Бот запущено. Опитування повідомлень...")
    application.run_polling()


if __name__ == '__main__':
    main()
