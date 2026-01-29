"""Настройка логирования с ротацией файлов."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from valutatrade_hub.infra.settings import get_settings

_logger: logging.Logger | None = None
_initialized: bool = False


def setup_logging(
    level: int = logging.INFO,
    console_level: int = logging.WARNING,
    log_file: Path | str | None = None,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 3,
) -> logging.Logger:
    """Создает логгер: файл + консоль."""
    global _logger, _initialized

    if _initialized and _logger is not None:
        return _logger

    settings = get_settings()
    if log_file is None:
        log_file = settings.log_path
    if isinstance(log_file, str):
        log_file = Path(log_file)

    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("valutatrade")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    file_fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    console_fmt = logging.Formatter(fmt="%(levelname)s: %(message)s")

    file_handler = RotatingFileHandler(
        filename=str(log_file), maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(file_fmt)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(console_fmt)
    logger.addHandler(console_handler)

    _logger = logger
    _initialized = True
    return logger


def get_logger(name: str = "valutatrade") -> logging.Logger:
    """Получить именованный логгер, если надо — настроит."""
    global _logger, _initialized
    if not _initialized:
        setup_logging()
    return logging.getLogger(f"valutatrade.{name}")
