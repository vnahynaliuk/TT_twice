from pathlib import Path

DOWNLOADS_DIR = Path("downloads")
DOWNLOADS_DIR.mkdir(exist_ok=True)

SUPPORTED_PLATFORMS = ['tiktok.com', 'youtube.com', 'youtu.be', 'twitter.com', 'x.com', 'instagram.com']
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
DOWNLOAD_TIMEOUT = 300
CLEANUP_INTERVAL = 24 * 60 * 60
