"""Доменные модели приложения."""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime
from typing import Any

from valutatrade_hub.core.exceptions import ValidationError


class User:
    """Пользователь системы: хранит имя и защищённый пароль."""

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

    # ---------- фабрики ----------
    @classmethod
    def create_new(cls, user_id: int, username: str, password: str) -> "User":
        """Создать пользователя, автоматически захешировав пароль."""
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
        """Восстановить пользователя из словаря (например, из JSON)."""
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

    # ---------- преобразования ----------
    def to_dict(self) -> dict[str, Any]:
        """Преобразовать в словарь для хранения."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "hashed_password": self._hashed_password,
            "salt": self._salt,
            "registration_date": self._registration_date.isoformat(),
        }

    def get_user_info(self) -> dict[str, Any]:
        """Информация о пользователе без пароля."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat(),
        }

    # ---------- операции с паролем ----------
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

    # ---------- вспомогательные ----------
    @staticmethod
    def _generate_salt() -> str:
        return os.urandom(16).hex()

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()

    # ---------- свойства ----------
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


# Заглушки для последующих шагов
class Wallet:  # pragma: no cover - будет реализован в следующем шаге
    pass


class Portfolio:  # pragma: no cover - будет реализован в следующем шаге
    pass
