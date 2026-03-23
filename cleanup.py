import logging
import time
from config import DOWNLOADS_DIR, CLEANUP_INTERVAL

logger = logging.getLogger(__name__)


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
