"""Обновление курсов: тянем из API и сохраняем."""

from __future__ import annotations

from valutatrade_hub.infra.settings import get_settings
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
        get_settings().get("last_refresh") or None  # not used; just to satisfy type

        crypto = self.crypto_client.fetch_rates()
        if crypto:
            crypto["_meta"] = {"updated_at": self._utc_now_iso()}
            self.storage.db.save_crypto_rates(crypto)

        fiat = self.fiat_client.fetch_rates()
        if fiat:
            fiat["_meta"] = {"updated_at": self._utc_now_iso()}
            self.storage.db.save_fiat_rates(fiat)

        self.logger.info("Курсы обновлены")

    @staticmethod
    def _utc_now_iso() -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()


def run_once() -> None:
    """Запускает одно обновление, удобный шорткат."""
    RatesUpdater().update()
