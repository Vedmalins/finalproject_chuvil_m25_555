"""Планировщик обновлений курсов с паузами."""

from __future__ import annotations

import threading
import time

from valutatrade_hub.logging_config import get_logger
from valutatrade_hub.parser_service.config import UPDATE_INTERVAL
from valutatrade_hub.parser_service.updater import RatesUpdater


class RatesScheduler:
    """Запускает updater по кругу в отдельном потоке."""

    def __init__(self, interval: int = UPDATE_INTERVAL) -> None:
        self.interval = interval
        self.updater = RatesUpdater()
        self.logger = get_logger("scheduler")
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Старт фонового потока."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self.logger.info("Планировщик запущен")

    def stop(self) -> None:
        """Остановка фонового потока."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1)
        self.logger.info("Планировщик остановлен")

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.updater.update()
            except Exception as e:
                self.logger.error(f"Ошибка в цикле обновления: {e}")
            self._stop_event.wait(self.interval)


def start_scheduler(interval: int = UPDATE_INTERVAL) -> RatesScheduler:
    """Удобный запуск планировщика."""
    scheduler = RatesScheduler(interval)
    scheduler.start()
    return scheduler
