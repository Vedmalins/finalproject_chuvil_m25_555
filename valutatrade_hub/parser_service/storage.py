"""Хранилище курсов: обёртка над DatabaseManager для удобства."""

from __future__ import annotations

from valutatrade_hub.infra.database import get_database


class RatesStorage:
    """Работает с курсами, читает и пишет в файлы через DB менеджер."""

    def __init__(self) -> None:
        self.db = get_database()

    def get_crypto_rate(self, code: str) -> float | None:
        """Курс крипты к USD."""
        rates = self.db.get_crypto_rates()
        code = code.upper()
        if code in rates:
            return rates[code].get("usd")
        return None

    def get_fiat_rate(self, code: str) -> float | None:
        """Курс фиата к USD (переворачиваем, в файле хранится USD->валюта)."""
        rates = self.db.get_fiat_rates()
        code = code.upper()
        if code == "USD":
            return 1.0
        if "rates" in rates and code in rates["rates"]:
            usd_to_currency = rates["rates"][code]
            if usd_to_currency and usd_to_currency != 0:
                return 1 / usd_to_currency
        return None

    def get_rate(self, code: str) -> float | None:
        """Общий метод: сначала крипта, потом фиат."""
        rate = self.get_crypto_rate(code)
        if rate is not None:
            return rate
        return self.get_fiat_rate(code)

    def get_all_rates(self) -> dict[str, float]:
        """Все курсы к USD, без метаданных."""
        result: dict[str, float] = {}

        crypto = self.db.get_crypto_rates()
        for code, data in crypto.items():
            if code.startswith("_"):
                continue
            if isinstance(data, dict) and "usd" in data:
                result[code] = data["usd"]

        fiat = self.db.get_fiat_rates()
        if "rates" in fiat:
            for code, rate in fiat["rates"].items():
                if code == "USD":
                    result[code] = 1.0
                elif rate and rate != 0:
                    result[code] = 1 / rate

        return result


def get_storage() -> RatesStorage:
    """Возвращает экземпляр хранилища курсов."""
    return RatesStorage()
