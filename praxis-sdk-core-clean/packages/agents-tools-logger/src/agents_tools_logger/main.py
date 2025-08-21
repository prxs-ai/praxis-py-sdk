import sys
from typing import Union

from loguru import logger

# Настройка логгера
logger.remove()  # Удаляем стандартный хендлер
logger.add(
    sys.stdout,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {file}:{line} - {message}",
    level="INFO",
    colorize=True
)
logger.add(
    "app.log",
    rotation="10 MB",
    compression="zip",
    level="ERROR",
    backtrace=True,
    diagnose=True
)


def log_message(message: str, level: str = "INFO", exception: Union[Exception, None] = None) -> None:
    """Упрощенное логирование с обработкой исключений"""
    if exception:
        logger.opt(exception=exception).log(level, message)
    else:
        logger.log(level, message)


log = logger

if __name__ == "__main__":
    log_message("This is an info message.")
    try:
        1 / 0
    except ZeroDivisionError as e:
        log_message("An error occurred!", level="ERROR", exception=e)
