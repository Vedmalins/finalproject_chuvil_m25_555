"""Хранилище курсов: обёртка над DatabaseManager для удобства."""

from __future__ import annotations

from valutatrade_hub.infra.database import get_database


class RatesStorage:
    """Работает с курсами, читает и пишет в файлы через DB менеджер."""

    def __init__(self) -> None:
        self.db = get_database()

    def get_crypto_rate(self, code: str) -> float | None:
        """Курс крипты к USD."""
        cache = self.db.get_rates_cache()
        pairs = cache.get("pairs", {})
        key = f"{code.upper()}_USD"
        entry = pairs.get(key)
        if entry:
            return entry.get("rate")
        return None

    def get_fiat_rate(self, code: str) -> float | None:
        """Курс фиата к USD (переворачиваем, в файле хранится USD->валюта)."""
        cache = self.db.get_rates_cache()
        pairs = cache.get("pairs", {})
        code = code.upper()
        if code == "USD":
            return 1.0
        key = f"{code}_USD"
        # если есть прямой курс к USD
        if key in pairs:
            return pairs[key].get("rate")
        # иначе попробуем перевернуть USD->code
        reverse_key = f"USD_{code}"
        if reverse_key in pairs:
            rate = pairs[reverse_key].get("rate")
            if rate:
                return 1 / rate
        return None

    def get_rate(self, code: str) -> float | None:
        """Общий метод: сначала крипта, потом фиат."""
        rate = self.get_crypto_rate(code)
        if rate is not None:
            return rate
        return self.get_fiat_rate(code)

    def get_all_rates(self) -> dict[str, float]:
        """Все курсы к USD, без метаданных."""
        cache = self.db.get_rates_cache()
        pairs = cache.get("pairs", {})
        result: dict[str, float] = {}
        for pair, data in pairs.items():
            try:
                code, base = pair.split("_", 1)
            except ValueError:
                continue
            if base != "USD":
                continue
            rate = data.get("rate")
            if rate:
                result[code] = rate
        return result

    def get_rate_with_timestamp(self, code: str) -> tuple[float | None, str | None]:
        """Возвращает курс и время обновления для TTL-проверки."""
        cache = self.db.get_rates_cache()
        pairs = cache.get("pairs", {})
        key = f"{code.upper()}_USD"
        entry = pairs.get(key)
        if not entry:
            return None, None
        return entry.get("rate"), entry.get("updated_at") or cache.get("last_refresh")


def get_storage() -> RatesStorage:
    """Возвращает экземпляр хранилища курсов."""
    return RatesStorage()
