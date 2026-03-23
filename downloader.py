"""
Telegram Bot для завантаження відео
Завантажує відео з TikTok, Instagram Reels, YouTube та Twitter/X
"""

import logging
import os
import re
import subprocess
import time
import asyncio
import json
import glob
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update, BotCommand, InputMediaPhoto, InputMediaVideo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import instaloader

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

DOWNLOADS_DIR = Path("downloads")
DOWNLOADS_DIR.mkdir(exist_ok=True)

SUPPORTED_PLATFORMS = ['tiktok.com', 'youtube.com', 'youtu.be', 'twitter.com', 'x.com', 'instagram.com']
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
DOWNLOAD_TIMEOUT = 300
CLEANUP_INTERVAL = 24 * 60 * 60


# ============================================================================
# ОЧИЩЕННЯ СТАРИХ ЗАВАНТАЖЕНЬ
# ============================================================================

def cleanup_old_downloads():
    try:
        current_time = time.time()
        deleted_count = 0
        for file_path in DOWNLOADS_DIR.iterdir():
            if file_path.is_file():
                if current_time - file_path.stat().st_mtime > CLEANUP_INTERVAL:
                    file_path.unlink()
                    deleted_count += 1
                    logger.info(f"Видалено старий файл: {file_path.name}")
        if deleted_count > 0:
            logger.info(f"Очищення завершено: видалено {deleted_count} старих файлів")
    except Exception as e:
        logger.error(f"Помилка при очищенні: {str(e)}")


async def cleanup_task(context):
    cleanup_old_downloads()
    logger.info("Автоматичне очищення завершено")


# ============================================================================
# ОБРОБНИКИ КОМАНД
# ============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    help_text = """
📖 **Доступні команди:**
/start_pohnaly - Привіт
/help_me_please - Показати цю довідку
/who_asked - Про цього бота

🔗 **Підтримувані платформи:**
- TikTok - відео
- Instagram - відео, рілз та фото
- YouTube - відео та Shorts (зберігає aspect ratio)
- Twitter/X - відео

📸 **Функціонал:**
- Завантаження відео
- Завантаження фото з Instagram (до 10 фото)
- Копіювання описів як цитати
- Автоматична очистка файлів (24 години)

⚠️ **Обмеження:**
- Максимальний розмір файлу: 50MB
- Час очікування завантаження: 5 хвилин
    """
    await update.message.reply_text(help_text)


async def about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    about_text = """
🤖 **Бот для завантаження відео**

Бот для завантаження відео з TikTok, Instagram Reels та YouTube.
Створено для клух !!!!!!
    """
    await update.message.reply_text(about_text)


async def cleanup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cleanup_old_downloads()
    await update.message.reply_text("✅ Очищення завершено! Старі завантаження видалені.")


async def vlop_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message_text = update.message.text.lower()
    if 'vlop' in message_text or 'влоп' in message_text:
        await update.message.reply_text("https://youtu.be/lhOuMYtQ94M?si=-2d0ejWlBlq8NwyO")


# ============================================================================
# ЗАВАНТАЖЕННЯ З INSTAGRAM
# ============================================================================

def download_instagram_files(url: str, output_dir: Path) -> list:
    """Завантажити фото або відео з Instagram через instaloader."""
    output_dir.mkdir(parents=True, exist_ok=True)

    ig_login = os.getenv("INSTAGRAM_LOGIN")
    ig_password = os.getenv("INSTAGRAM_PASSWORD")

    match = re.search(r'/(?:p|reel|tv)/([A-Za-z0-9_-]+)', url)
    if not match:
        logger.error("Не вдалося витягти shortcode з URL")
        return []

    shortcode = match.group(1)
    logger.info(f"Instagram shortcode: {shortcode}")

    L = instaloader.Instaloader(
        download_videos=True,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        post_metadata_txt_pattern="",
        dirname_pattern=str(output_dir),
        filename_pattern="{shortcode}_{mediaid}"
    )

    try:
        if ig_login and ig_password:
            L.login(ig_login, ig_password)
            logger.info(f"Залогінено в Instagram як {ig_login}")
    except Exception as e:
        logger.warning(f"Не вдалося залогінитись: {e}")

    try:
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        L.download_post(post, target=output_dir)
    except Exception as e:
        logger.error(f"Помилка instaloader: {e}")
        return []

    files = [
        f for f in glob.glob(str(output_dir / "**/*"), recursive=True)
        if os.path.isfile(f) and f.endswith(('.jpg', '.mp4', '.png'))
    ]
    logger.info(f"instaloader завантажив: {files}")
    return files


# ============================================================================
# ОБРОБНИК ЗАВАНТАЖЕННЯ ВІДЕО
# ============================================================================

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message_text = update.message.text
    if not message_text:
        return

    urls_found = []
    for word in message_text.split():
        if word.startswith(('http://', 'https://')):
            urls_found.append(word.strip())

    is_reply_to_bot = (update.message.reply_to_message and
                       update.message.reply_to_message.from_user.is_bot)

    if is_reply_to_bot and not urls_found:
        await update.message.reply_text("МІША ВСЬО ХУЙНЯ ДАВАЙ СНАЧАЛА")
        return

    if not urls_found:
        return

    for url in urls_found:
        if not any(platform in url for platform in SUPPORTED_PLATFORMS):
            continue

        status_message = await update.message.reply_text(f"⏳ Не ссикуй щас буде. Обробляю: {url}")

        try:
            timestamp = int(time.time() * 1000000)

            # ----------------------------------------------------------------
            # INSTAGRAM
            # ----------------------------------------------------------------
            if 'instagram.com' in url:
                output_dir = DOWNLOADS_DIR / f"ig_{timestamp}"

                downloaded = await asyncio.to_thread(
                    download_instagram_files, url, output_dir
                )

                if not downloaded:
                    await status_message.edit_text("❌ Не вдалося завантажити з Instagram")
                    continue

                if len(downloaded) == 1:
                    f = downloaded[0]
                    if f.lower().endswith(('.mp4', '.mov', '.webm', '.mkv')):
                        with open(f, 'rb') as video:
                            await update.message.reply_video(video=video)
                    else:
                        with open(f, 'rb') as photo:
                            await update.message.reply_photo(photo=photo)
                else:
                    media_group = []
                    for f in downloaded[:10]:
                        if f.lower().endswith(('.mp4', '.mov', '.webm', '.mkv')):
                            media_group.append(InputMediaVideo(open(f, 'rb')))
                        else:
                            media_group.append(InputMediaPhoto(open(f, 'rb')))
                    await update.message.reply_media_group(media=media_group)

                for f in downloaded:
                    try:
                        os.remove(f)
                    except Exception:
                        pass
                try:
                    output_dir.rmdir()
                except Exception:
                    pass

                await status_message.delete()
                continue

            # ----------------------------------------------------------------
            # TIKTOK / YOUTUBE / TWITTER
            # ----------------------------------------------------------------
            output_path = DOWNLOADS_DIR / f"video_{timestamp}.%(ext)s"

            info_cmd = ["yt-dlp", "-j", "--no-warnings", url]
            try:
                info_result = subprocess.run(info_cmd, capture_output=True, text=True, timeout=30)
                video_info = json.loads(info_result.stdout) if info_result.stdout else {}
                description = video_info.get('description', '').strip()
            except Exception as e:
                logger.warning(f"Не вдалося отримати метаінформацію: {e}")
                description = ""

            cmd = [
                "yt-dlp",
                "-f", "bestvideo+bestaudio/best",
                "-o", str(output_path),
                url
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=DOWNLOAD_TIMEOUT)

            if result.returncode != 0:
                logger.error(f"МИ як фурі, ПОМИЛКА ПРИРОДИ: {result.stderr}")
                error_msg = result.stderr[:200] if result.stderr else "Невідома помилка"
                await status_message.edit_text(f"Завантаження не вдалося.\n\nПомилка: {error_msg}")
                continue

            downloaded_files = glob.glob(str(DOWNLOADS_DIR / f"video_{timestamp}.*"))

            if not downloaded_files:
                await status_message.edit_text("Файл не знайдено після завантаження")
                continue

            video_file = downloaded_files[0]
            file_size = os.path.getsize(video_file)

            if file_size > MAX_FILE_SIZE:
                os.remove(video_file)
                size_mb = file_size / 1024 / 1024
                max_mb = MAX_FILE_SIZE / 1024 / 1024
                await status_message.edit_text(
                    f"Відео занадто велике ({size_mb:.1f}MB).\n"
                    f"Максимальний розмір {max_mb:.0f}MB"
                )
                continue

            await status_message.edit_text("Завантажую в Telegram...")

            if description:
                lines = description.split('\n')
                quoted_lines = ['> ' + line for line in lines if line.strip()]
                caption = '\n'.join(quoted_lines)[:1024]
            else:
                caption = "ПЕРЕМОГА БУДЕ!"

            with open(video_file, 'rb') as f:
                await update.message.reply_video(
                    video=f,
                    caption=caption,
                    parse_mode="MarkdownV2"
                )

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
