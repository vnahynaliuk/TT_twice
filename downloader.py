"""
Telegram Bot для завантаження відео
Завантажує відео з TikTok, Instagram Reels, YouTube та Twitter/X
"""

import logging
import os
import subprocess
import time
import asyncio
import json
import glob
import urllib.request
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

try:
    from instagrapi import Client as InstaClient
    INSTAGRAPI_AVAILABLE = True
except ImportError:
    INSTAGRAPI_AVAILABLE = False
    logger_temp = logging.getLogger(__name__)
    logger_temp.warning("instagrapi не встановлено, Instagram фото не будуть завантажуватися")

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
• Instagram - відео та фото
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


async def vlop_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробник для слів vlop/влоп."""
    message_text = update.message.text.lower()
    if 'vlop' in message_text or 'влоп' in message_text:
        await update.message.reply_text("https://youtu.be/lhOuMYtQ94M?si=-2d0ejWlBlq8NwyO")


async def download_instagram(url: str) -> list:
    """Завантажити фото/відео з Instagram через instagrapi."""
    if not INSTAGRAPI_AVAILABLE:
        raise Exception("instagrapi не встановлено")
    
    try:
        cl = InstaClient()
        
        # Отримати ID з URL
        media_pk = cl.media_pk_from_url(url)
        
        # Отримати інформацію про медіа
        media = cl.media_info(media_pk)
        
        # Список файлів що були завантажені
        downloaded_files = []
        
        # Обробити в залежності від типу
        if media.media_type == 1:  # Фото
            file_path = DOWNLOADS_DIR / f"insta_{int(time.time() * 1000000)}.jpg"
            media.set_user(cl.user_info(media.user.pk))
            
            # Завантажити фото
            photo_url = media.image_versions2.candidates[0].url
            urllib.request.urlretrieve(photo_url, str(file_path))
            downloaded_files.append(str(file_path))
            
        elif media.media_type == 8:  # Альбом (carousel)
            for idx, carousel_item in enumerate(media.carousel_media):
                if carousel_item.media_type == 1:  # Фото в альбомі
                    file_path = DOWNLOADS_DIR / f"insta_{int(time.time() * 1000000)}_carousel_{idx}.jpg"
                    photo_url = carousel_item.image_versions2.candidates[0].url
                    urllib.request.urlretrieve(photo_url, str(file_path))
                    downloaded_files.append(str(file_path))
                elif carousel_item.media_type == 2:  # Відео в альбомі
                    file_path = DOWNLOADS_DIR / f"insta_{int(time.time() * 1000000)}_carousel_{idx}.mp4"
                    video_url = carousel_item.video_url
                    urllib.request.urlretrieve(video_url, str(file_path))
                    downloaded_files.append(str(file_path))
        elif media.media_type == 2:  # Відео (реел)
            file_path = DOWNLOADS_DIR / f"insta_{int(time.time() * 1000000)}.mp4"
            video_url = media.video_url
            urllib.request.urlretrieve(video_url, str(file_path))
            downloaded_files.append(str(file_path))
        
        return downloaded_files
        
    except Exception as e:
        logger.error(f"Помилка завантаження Instagram: {e}")
        raise


# ============================================================================
# ОБРОБНИК ЗАВАНТАЖЕННЯ ВІДЕО
# ============================================================================

async def vlop_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробник для слів vlop/влоп."""
    message_text = update.message.text.lower()
    if 'vlop' in message_text or 'влоп' in message_text:
        await update.message.reply_text("https://youtu.be/lhOuMYtQ94M?si=-2d0ejWlBlq8NwyO")

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
    
    # Перевірити чи це реплай на бота (у відповіді)
    is_reply_to_bot = (update.message.reply_to_message and 
                       update.message.reply_to_message.from_user.is_bot)
    
    # Якщо це реплай на бота, але посилань нема - відповісти на дурість
    if is_reply_to_bot and not urls_found:
        await update.message.reply_text("МІША ВСЬО ХУЙНЯ ДАВАЙ СНАЧАЛА")
        return
    
    # Якщо посилань не знайдено в звичайному повідомленні
    if not urls_found:
        return
    
    # Обробити кожне посилання
    for url in urls_found:
        # Перевірити, чи платформа підтримується
        if not any(platform in url for platform in SUPPORTED_PLATFORMS):
            continue
        
        # Визначити чи це Instagram
        is_instagram = 'instagram.com' in url
        
        # Відправити повідомлення про обробку
        status_message = await update.message.reply_text(f"⏳ Не ссикуй щас буде. Обробляю: {url}")
        
        try:
            # Для Instagram спочатку спробувати instagrapi
            if is_instagram and INSTAGRAPI_AVAILABLE:
                try:
                    downloaded_files = await asyncio.to_thread(download_instagram, url)
                    
                    if downloaded_files:
                        # Отримати опис через yt-dlp (якщо можна)
                        description = ""
                        try:
                            info_cmd = ["yt-dlp", "-j", "--no-warnings", url]
                            info_result = subprocess.run(info_cmd, capture_output=True, text=True, timeout=30)
                            video_info = json.loads(info_result.stdout) if info_result.stdout else {}
                            description = video_info.get('description', '').strip()
                        except:
                            pass
                        
                        # Відправити кожен файл
                        for video_file in downloaded_files:
                            if os.path.exists(video_file):
                                file_size = os.path.getsize(video_file)
                                
                                if file_size > MAX_FILE_SIZE:
                                    os.remove(video_file)
                                    size_mb = file_size / 1024 / 1024
                                    max_mb = MAX_FILE_SIZE / 1024 / 1024
                                    await status_message.edit_text(
                                        f"Файл занадто великий ({size_mb:.1f}MB).\n"
                                        f"Максимальний розмір {max_mb:.0f}MB"
                                    )
                                    continue
                                
                                await status_message.edit_text("Завантажую в Telegram...")
                                
                                # Підготувати caption
                                if description:
                                    lines = description.split('\n')
                                    quoted_lines = ['> ' + line for line in lines if line.strip()]
                                    caption = '\n'.join(quoted_lines)[:1024]
                                else:
                                    caption = "ПЕРЕМОГА БУДЕ!"
                                
                                # Визначити тип файлу
                                ext = os.path.splitext(video_file)[1].lower()
                                
                                with open(video_file, 'rb') as f:
                                    if ext in ['.jpg', '.jpeg', '.png', '.gif']:
                                        await update.message.reply_photo(
                                            photo=f,
                                            caption=caption,
                                            parse_mode="MarkdownV2"
                                        )
                                    else:
                                        await update.message.reply_video(
                                            video=f,
                                            caption=caption,
                                            parse_mode="MarkdownV2"
                                        )
                                
                                os.remove(video_file)
                        
                        await status_message.delete()
                        continue
                        
                except Exception as e:
                    logger.warning(f"instagrapi не спрацював для {url}: {e}")
                    # Продовжити з yt-dlp як fallback
            
            # Створити унікальне ім'я файлу на основі часу
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
            
            # Використовувати yt-dlp для всіх типів контенту
            # Для Instagram фото bestvideo буде jpg/png
            # Для відео буде mp4
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

    # Додати обробник для vlop/влоп (має бути перед download_video)
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'(vlop|влоп)'), vlop_handler))
    
    # Додати обробник повідомлень для посилань на відео
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))

    # Почати опитування повідомлень
    logger.info("Бот запущено. Опитування повідомлень...")
    application.run_polling()


if __name__ == '__main__':
    main()
