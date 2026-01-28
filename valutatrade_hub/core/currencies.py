"""Простой списочек валют, чтоб не забыть что поддерживаем (потом может поправлю)."""

from __future__ import annotations

from typing import Iterable

from valutatrade_hub.core.exceptions import InvalidCurrencyError

# Поддерживаемые валюты (базовый набор из итогового проекта)
SUPPORTED_CURRENCIES: tuple[str, ...] = (
    "USD",
    "EUR",
    "GBP",
    "RUB",
    "BTC",
    "ETH",
    "SOL",
)


def get_supported_currencies() -> tuple[str, ...]:
    """Вернуть кортеж кодов поддерживаемых валют."""
    return SUPPORTED_CURRENCIES


def is_supported(code: str) -> bool:
    """Проверка, что валюта есть в списке SUPPORTED_CURRENCIES."""
    return code.upper() in SUPPORTED_CURRENCIES


def ensure_supported(code: str) -> str:
    """Вернуть верхний регистр кода или бросить InvalidCurrencyError."""
    upper = code.upper()
    if not is_supported(upper):
        raise InvalidCurrencyError(upper)
    return upper


def format_pair_key(base: str, quote: str) -> str:
    """Сформировать ключ пары, например BTC_USD."""
    return f"{base.upper()}_{quote.upper()}"


def filter_supported(codes: Iterable[str]) -> list[str]:
    """Оставить только поддерживаемые коды валют."""
    return [c.upper() for c in codes if is_supported(c)]
