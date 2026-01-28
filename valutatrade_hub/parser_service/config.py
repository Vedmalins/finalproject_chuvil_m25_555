"""Конфиг парсера курсов, чтобы не хардкодить в коде."""

COINGECKO_API_URL = "https://api.coingecko.com/api/v3"
EXCHANGERATE_API_URL = "https://api.exchangerate-api.com/v4/latest"

# криптовалюты: код -> id в coingecko
CRYPTO_CURRENCIES = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "USDT": "tether",
}

# фиат: просто список поддерживаемых
FIAT_CURRENCIES = ["USD", "EUR", "RUB", "GBP"]

UPDATE_INTERVAL = 60  # секунды между обновлениями
REQUEST_TIMEOUT = 10
