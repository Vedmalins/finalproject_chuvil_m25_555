"""Классы валют и реестр, чтобы работать с кодами спокойно."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import ClassVar, Iterable

from valutatrade_hub.core.exceptions import CurrencyNotFoundError, InvalidCurrencyError


class Currency(ABC):
    """База для всех валют: хранит имя и код."""

    def __init__(self, name: str, code: str) -> None:
        if not name or not name.strip():
            raise ValueError("Имя валюты пустое")
        self._validate_code(code)
        self.name = name.strip()
        self.code = code.upper()

    @staticmethod
    def _validate_code(code: str) -> None:
        if not code:
            raise ValueError("Код валюты пустой")
        if not re.match(r"^[A-Z]{2,5}$", code.upper()):
            raise ValueError("Код должен быть 2-5 заглавных букв")

    @abstractmethod
    def get_display_info(self) -> str:
        """Строка для показа пользователю."""
        raise NotImplementedError

    def __str__(self) -> str:
        return f"{self.code} ({self.name})"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', code='{self.code}')"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Currency):
            return NotImplemented
        return self.code == other.code

    def __hash__(self) -> int:
        return hash(self.code)


class FiatCurrency(Currency):
    """Обычные деньги, добавляем страну-эмитент."""

    def __init__(self, name: str, code: str, issuing_country: str) -> None:
        if not issuing_country or not issuing_country.strip():
            raise ValueError("Страна эмитент пуста")
        super().__init__(name, code)
        self.issuing_country = issuing_country.strip()

    def get_display_info(self) -> str:
        return f"[FIAT] {self.code} — {self.name} (эмитент: {self.issuing_country})"

    def __repr__(self) -> str:
        return (
            f"FiatCurrency(name='{self.name}', code='{self.code}', "
            f"issuing_country='{self.issuing_country}')"
        )


class CryptoCurrency(Currency):
    """Криптовалюта, хранит алгоритм и капитализацию."""

    def __init__(self, name: str, code: str, algorithm: str, market_cap: float = 0.0) -> None:
        if not algorithm or not algorithm.strip():
            raise ValueError("Алгоритм пустой")
        if market_cap < 0:
            raise ValueError("Капитализация не может быть отрицательной")
        super().__init__(name, code)
        self.algorithm = algorithm.strip()
        self.market_cap = market_cap

    def get_display_info(self) -> str:
        cap = self._format_cap()
        return f"[CRYPTO] {self.code} — {self.name} | Алгоритм: {self.algorithm} | Кап: {cap}"

    def _format_cap(self) -> str:
        cap = self.market_cap
        if cap >= 1_000_000_000_000:
            return f"${cap/1_000_000_000_000:.2f}T"
        if cap >= 1_000_000_000:
            return f"${cap/1_000_000_000:.2f}B"
        if cap >= 1_000_000:
            return f"${cap/1_000_000:.2f}M"
        if cap > 0:
            return f"${cap:,.2f}"
        return "N/A"

    def __repr__(self) -> str:
        return (
            f"CryptoCurrency(name='{self.name}', code='{self.code}', "
            f"algorithm='{self.algorithm}', market_cap={self.market_cap})"
        )


# базовый набор, чтобы registry сразу работал
SUPPORTED_CURRENCIES: tuple[str, ...] = ("USD", "EUR", "GBP", "RUB", "BTC", "ETH", "SOL")


class CurrencyRegistry:
    """Регистрация и выдача валют."""

    _registry: ClassVar[dict[str, Currency]] = {}

    @classmethod
    def _init_registry(cls) -> None:
        if cls._registry:
            return
        fiat_list = [
            FiatCurrency("US Dollar", "USD", "USA"),
            FiatCurrency("Euro", "EUR", "EU"),
            FiatCurrency("British Pound Sterling", "GBP", "UK"),
            FiatCurrency("Russian Ruble", "RUB", "Russia"),
        ]
        crypto_list = [
            CryptoCurrency("Bitcoin", "BTC", "SHA-256"),
            CryptoCurrency("Ethereum", "ETH", "Ethash"),
            CryptoCurrency("Solana", "SOL", "Proof of History + PoS"),
        ]
        for cur in fiat_list + crypto_list:
            cls._registry[cur.code] = cur

    @classmethod
    def get_currency(cls, code: str) -> Currency:
        cls._init_registry()
        code = code.upper().strip()
        if code not in cls._registry:
            raise CurrencyNotFoundError(code)
        return cls._registry[code]

    @classmethod
    def register_currency(cls, currency: Currency) -> None:
        cls._init_registry()
        cls._registry[currency.code] = currency

    @classmethod
    def list_currencies(cls) -> list[Currency]:
        cls._init_registry()
        return list(cls._registry.values())

    @classmethod
    def list_fiat_currencies(cls) -> list[FiatCurrency]:
        cls._init_registry()
        return [c for c in cls._registry.values() if isinstance(c, FiatCurrency)]

    @classmethod
    def list_crypto_currencies(cls) -> list[CryptoCurrency]:
        cls._init_registry()
        return [c for c in cls._registry.values() if isinstance(c, CryptoCurrency)]

    @classmethod
    def is_valid_code(cls, code: str) -> bool:
        cls._init_registry()
        return code.upper().strip() in cls._registry


def get_supported_currencies() -> tuple[str, ...]:
    """Просто возвращает константу, пригодится в CLI."""
    return SUPPORTED_CURRENCIES


def is_supported(code: str) -> bool:
    return CurrencyRegistry.is_valid_code(code)


def ensure_supported(code: str) -> str:
    if not is_supported(code):
        raise InvalidCurrencyError(code)
    return code.upper()


def format_pair_key(base: str, quote: str) -> str:
    return f"{base.upper()}_{quote.upper()}"


def filter_supported(codes: Iterable[str]) -> list[str]:
    return [c.upper() for c in codes if is_supported(c)]
