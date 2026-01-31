"""Обновление курсов: тянем из API и сохраняем."""

from __future__ import annotations
from typing import Any

from valutatrade_hub.core.exceptions import ApiRequestError
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

    def update(self) -> dict[str, Any]:
        """Один цикл обновления: crypto + fiat. Возвращает итог для CLI."""
        timestamp = self._utc_now_iso()
        warnings: list[str] = []
        updated_sources: dict[str, int] = {"coingecko": 0, "exchangerate": 0}

        # 1) КРИПТА
        crypto = {}
        try:
            crypto = self.crypto_client.fetch_rates() or {}
            updated_sources["coingecko"] = len([k for k in crypto.keys() if not str(k).startswith("_")])
        except ApiRequestError as e:
            self.logger.warning(f"CoinGecko недоступен: {e}")
            warnings.append(f"CoinGecko: {e}")

        # 2) ФИАТ
        fiat = {}
        if self.fiat_client is None:
            msg = "EXCHANGERATE_API_KEY не задан — фиатные курсы пропущены"
            self.logger.warning(msg)
            warnings.append(msg)
        else:
            try:
                fiat = self.fiat_client.fetch_rates() or {}
                if isinstance(fiat, dict) and "rates" in fiat and isinstance(fiat["rates"], dict):
                    updated_sources["exchangerate"] = len(fiat["rates"])
            except ApiRequestError as e:
                self.logger.warning(f"ExchangeRate-API недоступен: {e}")
                warnings.append(f"ExchangeRate-API: {e}")

        # 3) текущая логика обновления pairs + сохранение rates.json
        existing_cache = self.storage.db.get_rates_cache() or {}
        pairs: dict[str, dict[str, str | float]] = existing_cache.get("pairs", {}).copy()

        # crypto --> pairs 
        if crypto:
            for code, data in crypto.items():
                if str(code).startswith("_"):
                    continue
                rate = data.get("usd") if isinstance(data, dict) else None
                if rate is None:
                    continue
                pairs[f"{code}_USD"] = {
                    "rate": float(rate),
                    "updated_at": timestamp,
                    "source": "CoinGecko",
                }
        # fiat --> pairs
        if fiat and isinstance(fiat, dict) and "rates" in fiat:
            base = fiat.get("base", "USD")
            for code, usd_to_code in fiat["rates"].items():
                if usd_to_code in (None, 0):
                    continue
                if base == "USD":
                    pair_rate = 1 / usd_to_code
                    pair_key = f"{code}_USD"
                else:
                    pair_rate = usd_to_code
                    pair_key = f"{code}_{base}"
                pairs[pair_key] = {"rate": pair_rate, "updated_at": timestamp, "source": "ExchangeRate-API"}

        if pairs:
            cache = {"pairs": pairs, "last_refresh": timestamp}
            self.storage.db.save_rates_cache(cache)
            self.logger.info(f"Курсы обновлены, всего пар: {len(pairs)}")
        else:
            self.logger.warning("Не удалось получить ни одного курса")

        return {
            "ok": bool(pairs),
            "updated_pairs": len(pairs),
            "last_refresh": timestamp,
            "warnings": warnings,
            "sources": updated_sources,
        }

    @staticmethod
    def _utc_now_iso() -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()


def run_once() -> dict:
    """Запускает одно обновление, удобный шорткат."""
    return RatesUpdater().update()
