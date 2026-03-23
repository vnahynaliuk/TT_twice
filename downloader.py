"""
Telegram Bot для завантаження відео
Завантажує відео з TikTok, Instagram Reels, YouTube та Twitter/X
"""

import logging
import os
import subprocess
import time
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Завантажити змінні середовища з файлу .env
load_dotenv()

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Створити папку для завантажень
DOWNLOADS_DIR = Path("downloads")
DOWNLOADS_DIR.mkdir(exist_ok=True)

# Константи
SUPPORTED_PLATFORMS = ['tiktok.com', 'instagram.com', 'youtube.com', 'youtu.be', 'reels', 'twitter.com', 'x.com']
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
DOWNLOAD_TIMEOUT = 300  # 5 хвилин
CLEANUP_INTERVAL = 24 * 60 * 60  # 24 години в секундах


# ============================================================================
# ОЧИЩЕННЯ СТАРИХ ЗАВАНТАЖЕНЬ
# ============================================================================

def cleanup_old_downloads():
    """Видалити завантаження старші за 24 години."""
    try:
        current_time = time.time()
        deleted_count = 0
        
        for file_path in DOWNLOADS_DIR.iterdir():
            if file_path.is_file():
                file_mtime = file_path.stat().st_mtime
                
                if current_time - file_mtime > CLEANUP_INTERVAL:
                    file_path.unlink()
                    deleted_count += 1
                    logger.info(f"Видалено старий файл: {file_path.name}")
        
        if deleted_count > 0:
            logger.info(f"Очищення завершено: видалено {deleted_count} старих файлів")
        
    except Exception as e:
        logger.error(f"Помилка при очищенні: {str(e)}")


async def cleanup_task(context):
    """Автоматичне очищення кожні 24 години."""
    cleanup_old_downloads()
    logger.info("Автоматичне очищення завершено")


# ============================================================================
# ОБРОБНИКИ КОМАНД
# ============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробник команди /start."""
    user = update.effective_user
    welcome_text = f"""
👋 Привіт {user.mention_html()}!

Це ботік для завантаження відосів! Лєра нахуярила вам можливість завантажувати відео з:
✅ TikTok
✅ Instagram Reels(не тестила ІРА ФАС)
✅ YouTube (Shorts & повні відео)
✅ Twitter бо ми всі звідти

🔗 лінк на базу

Використайте /help для більше команд.
    """
    await update.message.reply_html(welcome_text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробник команди /help."""
    help_text = """
📖 **Доступні команди:**
/start - Привіт
/help - Показати цю довідку
/about - Про цього бота

🔗 **Підтримувані платформи:**
• TikTok (tiktok.com)
• Instagram Reels (instagram.com)
• YouTube (youtube.com, youtu.be)
• Twitter/X (twitter.com, x.com)

⚠️ **Обмеження:**
• Максимальний розмір файлу: 50MB
• Час очікування завантаження: 5 хвилин бо фреймворк не тяне більше
    """
    await update.message.reply_text(help_text)


async def about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробник команди /about."""
    about_text = """
🤖 **Бот для завантаження відео**

Бот для завантаження відео з TikTok, Instagram Reels та YouTube.
Створено для клух !!!!!!

    """
    await update.message.reply_text(about_text)


async def cleanup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробник команди /cleanup - вручну видалити старі завантаження."""
    cleanup_old_downloads()
    await update.message.reply_text("✅ Очищення завершено! Старі завантаження видалені.")


# ============================================================================
# ОБРОБНИК ЗАВАНТАЖЕННЯ ВІДЕО
# ============================================================================

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Завантажити відео за надане посилання."""
    url = update.message.text.strip()
    
    # Перевірити URL
    if not url.startswith(('http://', 'https://')):
        await update.message.reply_text("Міша всьо хуйня, давай по новой")
        return
    
    # Перевірити, чи платформа підтримується
    if not any(platform in url for platform in SUPPORTED_PLATFORMS):
        platforms_list = '\n'.join([f"• {p}" for p in SUPPORTED_PLATFORMS])
        await update.message.reply_text(
            f"Я СПИСОК ЗВІДКИ СКАЧУВАТИ КОМУ ПИСАЛА? \n\n**поки що можна звідси:**\n{platforms_list}"
        )
        return
    
    # Відправити повідомлення про обробку
    status_message = await update.message.reply_text("⏳ Не ссикуй щас буде.")
    
    try:
        # Створити унікальне ім'я файлу на основі часу
        import time
        timestamp = int(time.time())
        output_path = DOWNLOADS_DIR / f"video_{timestamp}.%(ext)s"
        
        # Підготувати команду yt-dlp
        cmd = [
            "yt-dlp",
            "-f", "best",
            "-o", str(output_path),
            url
        ]
        
        # Запустити завантаження
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=DOWNLOAD_TIMEOUT)
        
        if result.returncode != 0:
            logger.error(f"МИ як фурі, ПОМИЛКА ПРИРОДИ: {result.stderr}")
            error_msg = result.stderr[:200] if result.stderr else "Невідома помилка"
            await status_message.edit_text(f"Завантаження не вдалося.\n\nПомилка: {error_msg}")
            return
        
        # Знайти завантажений файл
        import glob
        downloaded_files = glob.glob(str(DOWNLOADS_DIR / f"video_{timestamp}.*"))
        
        if not downloaded_files:
            await status_message.edit_text("Файл не знайдено після завантаження")
            return
        
        video_file = downloaded_files[0]
        file_size = os.path.getsize(video_file)
        
        # Перевірити розмір файлу (ліміт Telegram 2GB, але ми обмежуємо до 50MB для безпеки)
        if file_size > MAX_FILE_SIZE:
            os.remove(video_file)
            size_mb = file_size / 1024 / 1024
            max_mb = MAX_FILE_SIZE / 1024 / 1024
            await status_message.edit_text(
                f"Відео занадто велике ({size_mb:.1f}MB).\n"
                f"Максимальний розмір {max_mb:.0f}MB"
            )
            return
        
        # Відправити відео користувачу
        await status_message.edit_text("Завантажую в Telegram...")
        
        with open(video_file, 'rb') as f:
            await update.message.reply_video(
                video=f,
                caption="ПЕРЕМОГА БУДЕ!"
            )
        
        # Очистити завантажений файл
        os.remove(video_file)
        await status_message.delete()
        
    except subprocess.TimeoutExpired:
        await status_message.edit_text("too long, не тяне фреймворк, попробуй скинуть по новой")
    except Exception as e:
        logger.error(f"Помилка завантаження відео: {str(e)}")
        error_msg = str(e)[:200]
        await status_message.edit_text(f"Сталася помилка:\n{error_msg}")


# ============================================================================
# НАЛАШТУВАННЯ БОТА
# ============================================================================

def main() -> None:
    """Запустити бота."""
    # Очистити старі файли при старті
    cleanup_old_downloads()
    logger.info("Очищення старих файлів завершено при старті бота")
    
    # Отримати токен зі змінної середовища
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN не знайдено в файлі .env")
    
    # Створити Application
    application = Application.builder().token(token).build()

    # Додати обробники команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about))
    application.add_handler(CommandHandler("cleanup", cleanup))

    # Додати обробник повідомлень для посилань на відео
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))

    # Почати опитування повідомлень
    logger.info("Бот запущено. Опитування повідомлень...")
    application.run_polling()


if __name__ == '__main__':
    main()
