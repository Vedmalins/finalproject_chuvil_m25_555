"""Модели проекта, пишу как студент, могу ошибаца, потом поправлю."""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime
from typing import Any

from valutatrade_hub.core.exceptions import InsufficientFundsError, ValidationError


class User:
    """Просто юзер: держим логин и хэш пароля, ничего магического."""

    MIN_PASSWORD_LENGTH = 4

    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime | None = None,
    ) -> None:
        if not username or not username.strip():
            raise ValidationError("Имя пользователя не может быть пустым")

        self._user_id = user_id
        self._username = username.strip()
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date or datetime.now()

    # фабрика: создаёт с нуля, сама солит/хешит
    @classmethod
    def create_new(cls, user_id: int, username: str, password: str) -> "User":
        """Сборка нового юзера, если пароль не слишком короткий."""
        if len(password) < cls.MIN_PASSWORD_LENGTH:
            raise ValidationError(
                f"Пароль должен быть минимум {cls.MIN_PASSWORD_LENGTH} символов"
            )

        salt = cls._generate_salt()
        hashed = cls._hash_password(password, salt)
        return cls(
            user_id=user_id,
            username=username,
            hashed_password=hashed,
            salt=salt,
            registration_date=datetime.now(),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "User":
        """Читает юзера из словаря (например из json)."""
        reg_date = data.get("registration_date")
        if isinstance(reg_date, str):
            try:
                reg_date = datetime.fromisoformat(reg_date.replace("Z", "+00:00"))
            except ValueError:
                reg_date = datetime.now()

        return cls(
            user_id=data["user_id"],
            username=data["username"],
            hashed_password=data["hashed_password"],
            salt=data["salt"],
            registration_date=reg_date,
        )

    # конвертация в dict для сохранения
    def to_dict(self) -> dict[str, Any]:
        """Возвращаю dict чтобы сохранить где-нибудь."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "hashed_password": self._hashed_password,
            "salt": self._salt,
            "registration_date": self._registration_date.isoformat(),
        }

    def get_user_info(self) -> dict[str, Any]:
        """Инфо про юзера без пароля, на всяк."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat(),
        }

    # работа с паролем
    def verify_password(self, password: str) -> bool:
        hashed = self._hash_password(password, self._salt)
        return secrets.compare_digest(hashed, self._hashed_password)

    def change_password(self, new_password: str) -> None:
        if len(new_password) < self.MIN_PASSWORD_LENGTH:
            raise ValidationError(
                f"Пароль должен быть минимум {self.MIN_PASSWORD_LENGTH} символов"
            )
        self._salt = self._generate_salt()
        self._hashed_password = self._hash_password(new_password, self._salt)

    # внутрянка
    @staticmethod
    def _generate_salt() -> str:
        return os.urandom(16).hex()

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()

    # свойства
    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        if not value or not value.strip():
            raise ValidationError("Имя пользователя не может быть пустым")
        self._username = value.strip()

    @property
    def registration_date(self) -> datetime:
        return self._registration_date

    def __str__(self) -> str:
        return f"User(id={self._user_id}, username='{self._username}')"

    def __repr__(self) -> str:
        return (
            f"User(user_id={self._user_id}, username='{self._username}', "
            f"registration_date='{self._registration_date.isoformat()}')"
        )


# кошелёк: держит баланс одной валюты
class Wallet:  # pragma: no cover
    """Кошелёк одной валюты: кладу/снимаю, смотрю баланс."""

    def __init__(self, currency_code: str, balance: float = 0.0) -> None:
        if not currency_code or not currency_code.strip():
            raise ValidationError("Код валюты не может быть пустым")

        self.currency_code = currency_code.upper().strip()
        self._balance = 0.0
        if balance != 0.0:
            self.balance = balance  # проходит через валидацию сеттера

    # фабрика из словаря
    @classmethod
    def from_dict(cls, currency_code: str, data: dict[str, Any]) -> "Wallet":
        return cls(currency_code=currency_code, balance=data.get("balance", 0.0))

    # обратно в dict
    def to_dict(self) -> dict[str, Any]:
        return {"balance": self._balance}

    # операции
    def deposit(self, amount: float) -> None:
        self._validate_amount(amount)
        self._balance += amount

    def withdraw(self, amount: float) -> None:
        self._validate_amount(amount)
        if amount > self._balance:
            raise InsufficientFundsError(
                available=self._balance, required=amount, code=self.currency_code
            )
        self._balance -= amount

    def get_balance_info(self) -> str:
        if self.currency_code in ("BTC", "ETH"):
            return f"{self.currency_code}: {self._balance:.8f}"
        if self.currency_code in ("SOL",):
            return f"{self.currency_code}: {self._balance:.6f}"
        return f"{self.currency_code}: {self._balance:.2f}"

    # валидация
    @staticmethod
    def _validate_amount(amount: float) -> None:
        if not isinstance(amount, (int, float)):
            raise ValidationError("Сумма должна быть числом")
        if amount <= 0:
            raise ValidationError("Сумма должна быть больше 0")

    # свойства
    @property
    def balance(self) -> float:
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        if not isinstance(value, (int, float)):
            raise ValidationError("Баланс должен быть числом")
        if value < 0:
            raise ValidationError("Баланс не может быть отрицательным")
        self._balance = float(value)

    def __str__(self) -> str:
        return self.get_balance_info()

    def __repr__(self) -> str:
        return f"Wallet(currency_code='{self.currency_code}', balance={self._balance})"


class Portfolio:  # pragma: no cover
    """Портфель юзера — словарик кошельков, без магии."""

    def __init__(self, user_id: int) -> None:
        self._user_id = user_id
        self._wallets: dict[str, Wallet] = {}

    # сборка из dict
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Portfolio":
        portfolio = cls(user_id=data["user_id"])
        for code, wallet_data in data.get("wallets", {}).items():
            portfolio._wallets[code] = Wallet.from_dict(code, wallet_data)
        return portfolio

    # обратно в dict
    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self._user_id,
            "wallets": {code: wallet.to_dict() for code, wallet in self._wallets.items()},
        }

    # операции над кошельками
    def add_currency(self, currency_code: str) -> None:
        code = currency_code.upper()
        if code not in self._wallets:
            self._wallets[code] = Wallet(code)

    def get_wallet(self, currency_code: str) -> Wallet | None:
        return self._wallets.get(currency_code.upper())

    def get_or_create_wallet(self, currency_code: str) -> Wallet:
        code = currency_code.upper()
        if code not in self._wallets:
            self._wallets[code] = Wallet(code)
        return self._wallets[code]

    def get_total_value(self, rates: dict[str, float], base: str = "USD") -> float:
        total = 0.0
        base = base.upper()
        for code, wallet in self._wallets.items():
            if code == base:
                total += wallet.balance
            else:
                pair = f"{code}_{base}"
                if pair in rates:
                    total += wallet.balance * rates[pair]
        return total

    # свойства
    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def wallets(self) -> dict[str, Wallet]:
        # отдаю копию, чтоб случайно не поломали
        return dict(self._wallets)

    def __str__(self) -> str:
        return f"Portfolio(user_id={self._user_id}, wallets={list(self._wallets.keys())})"

    def __repr__(self) -> str:
        return self.__str__()
