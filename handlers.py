import logging
import os
import glob
import json
import random
import subprocess
import asyncio
import time
import html
from pathlib import Path
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import ContextTypes
from config import DOWNLOADS_DIR, SUPPORTED_PLATFORMS, MAX_FILE_SIZE, DOWNLOAD_TIMEOUT
from cleanup import cleanup_old_downloads
from instagram import download_instagram_files
from replies import RANDOM_REPLIES

logger = logging.getLogger(__name__)


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
- TikTok - відео та фото/слайдшоу
- Instagram - відео, рілз та фото
- YouTube - відео та Shorts (зберігає aspect ratio)
- Twitter/X - відео та фото

📸 **Функціонал:**
- Завантаження відео
- Завантаження фото з Instagram (до 10 фото)
- Завантаження слайдшоу з TikTok
- Завантаження фото з Twitter/X
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
        await update.message.reply_text(random.choice(RANDOM_REPLIES))
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
            # TIKTOK ФОТО/СЛАЙДШОУ
            # ----------------------------------------------------------------
            if 'tiktok.com' in url and '/photo/' in url:
                output_dir = DOWNLOADS_DIR / f"tt_{timestamp}"
                output_dir.mkdir(parents=True, exist_ok=True)

                subprocess.run(
                    ["gallery-dl", "-d", str(output_dir), url],
                    capture_output=True, text=True, timeout=DOWNLOAD_TIMEOUT
                )

                files = [
                    f for f in glob.glob(str(output_dir / "**/*"), recursive=True)
                    if os.path.isfile(f) and f.lower().endswith(('.jpg', '.png', '.jpeg', '.webp'))
                ]

                if not files:
                    await status_message.edit_text("❌ Не вдалося завантажити слайдшоу з TikTok")
                    continue

                if len(files) == 1:
                    with open(files[0], 'rb') as photo:
                        await update.message.reply_photo(photo=photo)
                else:
                    media_group = []
                    for f in files[:10]:
                        media_group.append(InputMediaPhoto(open(f, 'rb')))
                    await update.message.reply_media_group(media=media_group)

                for f in files:
                    try:
                        os.remove(f)
                    except Exception:
                        pass

                await status_message.delete()
                continue

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
            # TIKTOK / YOUTUBE / TWITTER — спочатку yt-dlp, потім gallery-dl
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

            # yt-dlp не впорався — пробуємо gallery-dl (для фото з Twitter тощо)
            if result.returncode != 0:
                logger.info("yt-dlp не впорався, пробую gallery-dl...")
                output_dir = DOWNLOADS_DIR / f"gdl_{timestamp}"
                output_dir.mkdir(parents=True, exist_ok=True)

                r2 = subprocess.run(
                    ["gallery-dl", "-d", str(output_dir), url],
                    capture_output=True, text=True, timeout=DOWNLOAD_TIMEOUT
                )

                files = [
                    f for f in glob.glob(str(output_dir / "**/*"), recursive=True)
                    if os.path.isfile(f) and f.lower().endswith(('.jpg', '.png', '.jpeg', '.webp', '.mp4'))
                ]

                if not files:
                    error_msg = result.stderr[:200] if result.stderr else "Невідома помилка"
                    await status_message.edit_text(f"Завантаження не вдалося.\n\nПомилка: {error_msg}")
                    continue

                if len(files) == 1:
                    f = files[0]
                    if f.lower().endswith('.mp4'):
                        with open(f, 'rb') as video:
                            await update.message.reply_video(video=video)
                    else:
                        with open(f, 'rb') as photo:
                            await update.message.reply_photo(photo=photo)
                else:
                    media_group = []
                    for f in files[:10]:
                        if f.lower().endswith('.mp4'):
                            media_group.append(InputMediaVideo(open(f, 'rb')))
                        else:
                            media_group.append(InputMediaPhoto(open(f, 'rb')))
                    await update.message.reply_media_group(media=media_group)

                for f in files:
                    try:
                        os.remove(f)
                    except Exception:
                        pass

                await status_message.delete()
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
                safe_description = html.escape(description)
                caption = f"<blockquote>{safe_description}</blockquote>"[:1024]
            else:
                caption = "ПЕРЕМОГА БУДЕ!"

            with open(video_file, 'rb') as f:
                await update.message.reply_video(
                    video=f,
                    caption=caption,
                    parse_mode="HTML"
                )

            os.remove(video_file)
            await status_message.delete()

        except subprocess.TimeoutExpired:
            await status_message.edit_text("too long, не тяне фреймворк, попробуй скинуть по новой")
        except Exception as e:
            logger.error(f"Помилка завантаження відео: {str(e)}")
            error_msg = str(e)[:200]
            await status_message.edit_text(f"Сталася помилка:\n{error_msg}")
