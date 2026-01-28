"""Список валют, чтобы не забыть что поддерживаем (если что допишу позже)."""

from __future__ import annotations

from typing import Iterable

from valutatrade_hub.core.exceptions import InvalidCurrencyError

# базовый набор, ничего хитрого
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
    """Возвращаю кортеж всех кодов, на память."""
    return SUPPORTED_CURRENCIES


def is_supported(code: str) -> bool:
    """Просто проверка что валюта в списке, без магии."""
    return code.upper() in SUPPORTED_CURRENCIES


def ensure_supported(code: str) -> str:
    """Поднимаю InvalidCurrencyError если код левых рук."""
    upper = code.upper()
    if not is_supported(upper):
        raise InvalidCurrencyError(upper)
    return upper


def format_pair_key(base: str, quote: str) -> str:
    """Склеиваю пару типа BTC_USD (на всяк)."""
    return f"{base.upper()}_{quote.upper()}"


def filter_supported(codes: Iterable[str]) -> list[str]:
    """Отбрасываю всё лишнее, оставляю только известные валюты."""
    return [c.upper() for c in codes if is_supported(c)]
