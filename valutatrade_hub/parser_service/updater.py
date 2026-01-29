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

        timestamp = self._utc_now_iso()

        crypto = self.crypto_client.fetch_rates()
        fiat = self.fiat_client.fetch_rates()

        existing_cache = self.storage.db.get_rates_cache() or {}
        pairs: dict[str, dict[str, str | float]] = existing_cache.get("pairs", {}).copy()

        if crypto:
            for code, data in crypto.items():
                if code.startswith("_"):
                    continue
                rate = data.get("usd")
                if rate is None:
                    continue
                pairs[f"{code}_USD"] = {
                    "rate": rate,
                    "updated_at": timestamp,
                    "source": "CoinGecko",
                }

        if fiat and "rates" in fiat:
            base = fiat.get("base", "USD")
            for code, usd_to_code in fiat["rates"].items():
                if usd_to_code is None or usd_to_code == 0:
                    continue
                # Храним курс code->USD (обратный к base=USD)
                if base == "USD":
                    pair_rate = 1 / usd_to_code
                    pair_key = f"{code}_USD"
                else:
                    pair_rate = usd_to_code
                    pair_key = f"{code}_{base}"
                pairs[pair_key] = {
                    "rate": pair_rate,
                    "updated_at": timestamp,
                    "source": "ExchangeRate-API",
                }

        if pairs != existing_cache.get("pairs") or pairs:
            cache = {"pairs": pairs, "last_refresh": timestamp}
            self.storage.db.save_rates_cache(cache)
            self.logger.info(f"Курсы обновлены, всего пар: {len(pairs)}")
        else:
            self.logger.warning("Не удалось получить ни одного курса")

    @staticmethod
    def _utc_now_iso() -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()


def run_once() -> None:
    """Запускает одно обновление, удобный шорткат."""
    RatesUpdater().update()
