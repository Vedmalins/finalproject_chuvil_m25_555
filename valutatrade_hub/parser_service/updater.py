"""Обновление курсов: тянем из API и сохраняем."""

from __future__ import annotations

from valutatrade_hub.logging_config import get_logger
from valutatrade_hub.parser_service.api_clients import (
    create_crypto_client,
    create_fiat_client,
)
from valutatrade_hub.parser_service.storage import get_storage


class RatesUpdater:
    """Стягивает курсы крипты и фиата и кладет в хранилище."""

    def __init__(self) -> None:
        self.crypto_client = create_crypto_client()
        self.fiat_client = create_fiat_client()
        self.storage = get_storage()
        self.logger = get_logger("updater")

    def update(self) -> None:
        """Один цикл обновления: crypto + fiat."""
        crypto = self.crypto_client.fetch_rates()
        if crypto:
            self.storage.db.save_crypto_rates(crypto)
        fiat = self.fiat_client.fetch_rates()
        if fiat:
            self.storage.db.save_fiat_rates(fiat)
        self.logger.info("Курсы обновлены")


def run_once() -> None:
    """Запускает одно обновление, удобный шорткат."""
    RatesUpdater().update()
