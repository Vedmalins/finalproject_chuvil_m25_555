"""Клиенты для внешних API курсов: крипта и фиат."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import requests

from valutatrade_hub.logging_config import get_logger
from valutatrade_hub.parser_service.config import (
    COINGECKO_API_URL,
    CRYPTO_CURRENCIES,
    EXCHANGERATE_API_URL,
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
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            self.logger.error(f"Запрос к {url} упал: {e}")
            return {}


class CoinGeckoClient(BaseApiClient):
    """Клиент CoinGecko: тянет курсы крипты."""

    def __init__(self) -> None:
        super().__init__()
        self.base_url = COINGECKO_API_URL

    def fetch_rates(self) -> dict[str, Any]:
        """Возвращает словарь код -> {usd: rate}."""
        coin_ids = ",".join(CRYPTO_CURRENCIES.values())
        url = f"{self.base_url}/simple/price"
        params = {"ids": coin_ids, "vs_currencies": "usd"}

        data = self._make_request(url, params)
        if not data:
            self.logger.warning("Не удалось получить курсы крипты")
            return {}

        result: dict[str, Any] = {}
        for code, cid in CRYPTO_CURRENCIES.items():
            if cid in data:
                result[code] = data[cid]

        self.logger.info(f"Курсы крипты: {list(result.keys())}")
        return result


class ExchangeRateClient(BaseApiClient):
    """Клиент ExchangeRate: тянет курсы фиатных валют."""

    def __init__(self) -> None:
        super().__init__()
        self.base_url = EXCHANGERATE_API_URL

    def fetch_rates(self) -> dict[str, Any]:
        """USD база, фильтруем только нужные валюты."""
        url = f"{self.base_url}/USD"
        data = self._make_request(url)

        if not data or "rates" not in data:
            self.logger.warning("Не удалось получить курсы фиата")
            return {}

        filtered = {cur: data["rates"][cur] for cur in FIAT_CURRENCIES if cur in data["rates"]}
        result = {"base": "USD", "rates": filtered}
        self.logger.info(f"Курсы фиата: {list(filtered.keys())}")
        return result


def create_crypto_client() -> CoinGeckoClient:
    """Фабрика клиента для криптовалют."""
    return CoinGeckoClient()


def create_fiat_client() -> ExchangeRateClient:
    """Фабрика клиента для фиата."""
    return ExchangeRateClient()
