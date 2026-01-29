"""Клиенты для внешних API курсов: крипта и фиат."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import requests
from requests import Response

from valutatrade_hub.logging_config import get_logger
from valutatrade_hub.parser_service.config import (
    BASE_FIAT_CURRENCY,
    COINGECKO_API_URL,
    CRYPTO_ID_MAP,
    EXCHANGERATE_API_URL,
    EXCHANGERATE_API_KEY,
    FIAT_CURRENCIES,
    REQUEST_TIMEOUT,
)


class BaseApiClient(ABC):
    """Базовый клиент, задает интерфейс и общий запрос."""

    def __init__(self) -> None:
        self.logger = get_logger("api")

    @abstractmethod
    def fetch_rates(self) -> dict[str, Any]:
        """Получить курсы."""
        raise NotImplementedError

    def _make_request(self, url: str, params: dict | None = None) -> dict[str, Any]:
        """GET запрос с таймаутом, ошибки логируются."""
        try:
            resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as e:
            self.logger.error(f"Запрос к {url} не выполнен: {e}")
            return {}

        if not self._is_success(resp):
            self._log_bad_status(resp)
            return {}

        try:
            return resp.json()
        except ValueError:
            self.logger.error(f"Невалидный JSON от {url}")
            return {}

    def _is_success(self, resp: Response) -> bool:
        return 200 <= resp.status_code < 300

    def _log_bad_status(self, resp: Response) -> None:
        code = resp.status_code
        if code == 401:
            level = self.logger.warning
            msg = "401 Unauthorized"
        elif code == 429:
            level = self.logger.warning
            msg = "429 Too Many Requests"
        elif code >= 500:
            level = self.logger.error
            msg = f"{code} Server Error"
        else:
            level = self.logger.warning
            msg = f"{code} Unexpected status"
        level(f"{msg} для {resp.url}")


class CoinGeckoClient(BaseApiClient):
    """Клиент CoinGecko: тянет курсы крипты."""

    def __init__(self) -> None:
        super().__init__()
        self.base_url = COINGECKO_API_URL

    def fetch_rates(self) -> dict[str, Any]:
        """Возвращает словарь код -> {usd: rate}."""
        coin_ids = ",".join(CRYPTO_ID_MAP.values())
        url = f"{self.base_url}/simple/price"
        params = {"ids": coin_ids, "vs_currencies": "usd"}

        data = self._make_request(url, params)
        if not data:
            self.logger.warning("Не удалось получить курсы крипты")
            return {}

        result: dict[str, Any] = {}
        for code, cid in CRYPTO_ID_MAP.items():
            if cid in data:
                result[code] = data[cid]

        self.logger.info(f"Курсы крипты: {list(result.keys())}")
        return result


class ExchangeRateClient(BaseApiClient):
    """Клиент ExchangeRate: тянет курсы фиатных валют."""

    def __init__(self) -> None:
        super().__init__()
        self.base_url = EXCHANGERATE_API_URL
        self.api_key = EXCHANGERATE_API_KEY

    def fetch_rates(self) -> dict[str, Any]:
        """USD база, фильтруем только нужные валюты."""
        if not self.api_key:
            self.logger.error("EXCHANGERATE_API_KEY не задан, запросы к ExchangeRate отключены")
            return {}

        url = f"{self.base_url}/{self.api_key}/latest/{BASE_FIAT_CURRENCY}"
        data = self._make_request(url)

        if not data or data.get("result") != "success" or "conversion_rates" not in data:
            self.logger.warning("Не удалось получить курсы фиата")
            return {}

        conversion_rates = data["conversion_rates"]
        # If FIAT_CURRENCIES is defined, we previously filtered.
        # Requirement now: persist all rates returned by API.
        filtered = conversion_rates
        base_code = data.get("base_code") or BASE_FIAT_CURRENCY
        result = {"base": base_code, "rates": filtered}
        self.logger.info(f"Курсы фиата: {list(filtered.keys())}")
        return result


def create_crypto_client() -> CoinGeckoClient:
    """Фабрика клиента для криптовалют."""
    return CoinGeckoClient()


def create_fiat_client() -> ExchangeRateClient:
    """Фабрика клиента для фиата."""
    return ExchangeRateClient()
