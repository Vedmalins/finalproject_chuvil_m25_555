"""Конфиг парсера курсов, чтобы не хардкодить в коде."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_env() -> None:
    """Простейшая загрузка .env без сторонних зависимостей."""
    env_path = Path(".env")
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if key and key not in os.environ:
            os.environ[key] = value


_load_env()


@dataclass(slots=True)
class ParserConfig:
    """Конфигурация Parser Service."""

    EXCHANGERATE_API_KEY: str = os.getenv("EXCHANGERATE_API_KEY", "").strip()
    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"
    BASE_CURRENCY: str = "USD"
    FIAT_CURRENCIES: tuple[str, ...] = ("USD", "EUR", "RUB", "GBP")
    CRYPTO_CURRENCIES: tuple[str, ...] = ("BTC", "ETH", "SOL")
    CRYPTO_ID_MAP: dict[str, str] = field(
        default_factory=lambda: {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana"}
    )
    RATES_FILE_PATH: str = "data/rates.json"
    HISTORY_FILE_PATH: str = "data/exchange_rates.json"
    REQUEST_TIMEOUT: int = 10
    UPDATE_INTERVAL: int = 60


# экспортируем константы для совместимости существующего кода
CONFIG = ParserConfig()
COINGECKO_API_URL = CONFIG.COINGECKO_URL
EXCHANGERATE_API_URL = CONFIG.EXCHANGERATE_API_URL
EXCHANGERATE_API_KEY = CONFIG.EXCHANGERATE_API_KEY
BASE_FIAT_CURRENCY = CONFIG.BASE_CURRENCY
CRYPTO_ID_MAP = CONFIG.CRYPTO_ID_MAP
FIAT_CURRENCIES = list(CONFIG.FIAT_CURRENCIES)
UPDATE_INTERVAL = CONFIG.UPDATE_INTERVAL
REQUEST_TIMEOUT = CONFIG.REQUEST_TIMEOUT
