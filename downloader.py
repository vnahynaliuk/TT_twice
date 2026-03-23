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
from telegram import Update, BotCommand
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
/start_pohnaly - Привіт
/help_me_please - Показати цю довідку
/who_asked - Про цього бота

🔗 **Підтримувані платформи:**
• TikTok - відео
• Instagram Reels - відео
• Instagram Posts - фото (альбоми)
• YouTube - відео (зберігає aspect ratio)
• Twitter/X - відео

📸 **Функціонал:**
• Завантаження відео
• Завантаження фото (Instagram)
• Копіювання описів як цитати
• Автоматична очистка файлів (24 години)

⚠️ **Обмеження:**
• Максимальний розмір файлу: 50MB
• Час очікування завантаження: 5 хвилин
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
    # Отримати текст повідомлення
    message_text = update.message.text
    if not message_text:
        return
    
    # Пошук всіх посилань у повідомленні
    urls_found = []
    for word in message_text.split():
        if word.startswith(('http://', 'https://')):
            urls_found.append(word.strip())
    
    # Якщо посилань не знайдено
    if not urls_found:
        return
    
    # Обробити кожне посилання
    for url in urls_found:
        # Перевірити, чи платформа підтримується
        if not any(platform in url for platform in SUPPORTED_PLATFORMS):
            continue
        
        # Визначити тип контенту (фото або відео)
        is_instagram_photo = 'instagram.com' in url and '/p/' in url
        
        # Відправити повідомлення про обробку
        status_message = await update.message.reply_text(f"⏳ Не ссикуй щас буде. Обробляю: {url}")
        
        try:
            # Створити унікальне ім'я файлу на основі часу
            import time
            import json
            timestamp = int(time.time() * 1000000)  # мікросекунди для унікальності
            output_path = DOWNLOADS_DIR / f"video_{timestamp}.%(ext)s"
            
            # Спочатку отримати метаінформацію (опис)
            info_cmd = [
                "yt-dlp",
                "-j",
                "--no-warnings",
                url
            ]
            
            try:
                info_result = subprocess.run(info_cmd, capture_output=True, text=True, timeout=30)
                video_info = json.loads(info_result.stdout) if info_result.stdout else {}
                description = video_info.get('description', '').strip()
                title = video_info.get('title', '').strip()
            except Exception as e:
                logger.warning(f"Не вдалося отримати метаінформацію: {e}")
                description = ""
                title = ""
            
            # Вибрати правильну команду для завантаження
            if is_instagram_photo:
                # Використовувати gallery-dl для фото Instagram
                cmd = [
                    "gallery-dl",
                    "-o", str(DOWNLOADS_DIR),
                    url
                ]
            else:
                # Для відео використовувати yt-dlp з правильним форматом
                # bestvideo+bestaudio зберігає aspect ratio для широких відео
                cmd = [
                    "yt-dlp",
                    "-f", "bestvideo+bestaudio/best",
                    "-o", str(output_path),
                    url
                ]
            
            # Запустити завантаження
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=DOWNLOAD_TIMEOUT)
            
            if result.returncode != 0:
                logger.error(f"МИ як фурі, ПОМИЛКА ПРИРОДИ: {result.stderr}")
                error_msg = result.stderr[:200] if result.stderr else "Невідома помилка"
                await status_message.edit_text(f"Завантаження не вдалося.\n\nПомилка: {error_msg}")
                continue
            
            # Знайти завантажений файл
            import glob
            downloaded_files = glob.glob(str(DOWNLOADS_DIR / f"video_{timestamp}.*"))
            
            if not downloaded_files:
                await status_message.edit_text("Файл не знайдено після завантаження")
                continue
            
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
                continue
            
            # Відправити відео користувачу
            await status_message.edit_text("Завантажую в Telegram...")
            
            # Підготувати caption з опису у форматі blockquote
            if description:
                # Форматувати опис як blockquote (> на початку кожного рядка)
                lines = description.split('\n')
                quoted_lines = ['> ' + line for line in lines if line.strip()]
                caption = '\n'.join(quoted_lines)[:1024]  # Обмеження до 1024 символів
            else:
                caption = "ПЕРЕМОГА БУДЕ!"
            
            with open(video_file, 'rb') as f:
                await update.message.reply_video(
                    video=f,
                    caption=caption,
                    parse_mode="MarkdownV2"
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
    application.add_handler(CommandHandler("start_pohnaly", start))
    application.add_handler(CommandHandler("help_me_please", help_command))
    application.add_handler(CommandHandler("who_asked", about))
    application.add_handler(CommandHandler("cleanup", cleanup))

    # Встановити команди в Telegram
    async def set_commands(app):
        commands = [
            BotCommand("start_pohnaly", "Привіт"),
            BotCommand("help_me_please", "Показати цю довідку"),
            BotCommand("who_asked", "Про цього бота"),
            BotCommand("cleanup", "Очистити старі файли"),
        ]
        await app.bot.set_my_commands(commands)
        logger.info("Команди встановлені в Telegram")
    
    # Запустити встановлення команд при старті
    application.post_init = set_commands

    # Додати обробник повідомлень для посилань на відео
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))

    # Почати опитування повідомлень
    logger.info("Бот запущено. Опитування повідомлень...")
    application.run_polling()


if __name__ == '__main__':
    main()
