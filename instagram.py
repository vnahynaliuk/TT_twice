import logging
import os
import re
import glob
import subprocess
import instaloader
from pathlib import Path
from config import DOWNLOAD_TIMEOUT

logger = logging.getLogger(__name__)


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
