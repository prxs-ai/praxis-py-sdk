from loguru import logger
import sys

# Настройка логгера
logger.remove()  # Удаляем стандартный хендлер
logger.add(sys.stdout, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {file}:{line} - {message}", level="INFO")
logger.add("app.log", rotation="10 MB", compression="zip", level="ERROR")  # Логи в файл, с ротацией

log = logger
if __name__ == "__main__":
    logger.info("This is an info message.")
    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("An error occurred!")
