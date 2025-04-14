"""Модуль логгера"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging():
    """Метод для настройки логгера+"""
    # Создаем папку logs, если ее нет
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Базовые настройки логирования
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format)

    # Основной файловый обработчик с ротацией
    log_file = logs_dir / "app.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",  # 10 MB
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    # Настройка корневого логгера
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)

    # Дополнительно можно настроить логирование ошибок в отдельный файл
    error_file_handler = RotatingFileHandler(
        logs_dir / "errors.log",
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    error_file_handler.setFormatter(formatter)
    error_file_handler.setLevel(logging.ERROR)
    root_logger.addHandler(error_file_handler)
