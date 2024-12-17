import logging
import os.path

from infrastructure.configs.config import get_settings

settings = get_settings()


def init_logging(
    fname='logs.log',
    debug_fname='debug.log',
    mode='a',
    level=logging.DEBUG,
):
    logger = logging.getLogger()
    # Удаление предыдущих обработчиков
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Создание директории для логов, если она не существует
    if not os.path.exists(settings.LOGS_DIR):
        os.makedirs(settings.LOGS_DIR)

    logger.setLevel(level)

    # Формат логов
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s'
    )

    # FileHandler для записи всех логов, кроме DEBUG
    file_handler = logging.FileHandler(f'{settings.LOGS_DIR}/{fname}', mode=mode, encoding='utf-8')
    file_handler.setLevel(logging.INFO)  # Логи INFO и выше
    file_handler.setFormatter(formatter)

    # FileHandler для записи только DEBUG-логов
    debug_file_handler = logging.FileHandler(
        f'{settings.LOGS_DIR}/{debug_fname}', mode=mode, encoding='utf-8'
    )
    debug_file_handler.setLevel(logging.DEBUG)  # Только DEBUG логи
    debug_file_handler.setFormatter(formatter)

    # FileHandler для записи ошибок (ERROR и выше)
    error_file_handler = logging.FileHandler(
        f'{settings.LOGS_DIR}/error.{fname}', mode=mode, encoding='utf-8'
    )
    error_file_handler.setLevel(logging.ERROR)  # Логи ERROR и выше
    error_file_handler.setFormatter(formatter)

    # StreamHandler для вывода в консоль (INFO и выше)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)  # Логи INFO и выше для консоли
    console_handler.setFormatter(formatter)

    # Добавляем обработчики
    logger.addHandler(file_handler)
    logger.addHandler(debug_file_handler)
    logger.addHandler(error_file_handler)
    logger.addHandler(console_handler)
