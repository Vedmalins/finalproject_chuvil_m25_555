"""Конфиг парсера курсов, чтобы не хардкодить в коде."""

from __future__ import annotations

import os
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

COINGECKO_API_URL = "https://api.coingecko.com/api/v3"
EXCHANGERATE_API_URL = "https://v6.exchangerate-api.com/v6"
EXCHANGERATE_API_KEY = os.getenv("EXCHANGERATE_API_KEY", "").strip()

BASE_FIAT_CURRENCY = "USD"

# криптовалюты: код -> id в coingecko (только нужные тикеры, без tether)
CRYPTO_ID_MAP = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
}

# фиат: просто список поддерживаемых
FIAT_CURRENCIES = ["USD", "EUR", "RUB", "GBP"]

UPDATE_INTERVAL = 60  # секунды между обновлениями
REQUEST_TIMEOUT = 10
