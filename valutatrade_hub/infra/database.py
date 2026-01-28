"""Простейшая база на json, лежит рядом с данными."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from valutatrade_hub.infra.settings import get_settings


class DatabaseManager:
    """Singleton для работы с файлами users/portfolios/rates."""

    _instance: "DatabaseManager | None" = None
    _data_dir: Path

    def __new__(cls, data_dir: Path | None = None) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            settings = get_settings()
            cls._data_dir = data_dir or settings.data_dir
            cls._data_dir.mkdir(parents=True, exist_ok=True)
            cls._instance._init_files()
        return cls._instance

    def _init_files(self) -> None:
        """Создает пустые json если их нет."""
        defaults = {
            "users.json": {},
            "portfolios.json": {},
            "rates.json": {},
            "exchange_rates.json": {},
        }
        for name, content in defaults.items():
            path = self._data_dir / name
            if not path.exists():
                self._write_json(path, content)

    def _read_json(self, path: Path) -> dict[str, Any]:
        """Чтение json, при ошибке отдает пустой словарь."""
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _write_json(self, path: Path, data: dict[str, Any]) -> None:
        """Запись json через временный файл чтобы не потерять данные."""
        temp = path.with_suffix(".tmp")
        with open(temp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(temp, path)

    # работа с пользователями
    def get_user(self, username: str) -> dict[str, Any] | None:
        users = self._read_json(self._data_dir / "users.json")
        return users.get(username)

    def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        users = self._read_json(self._data_dir / "users.json")
        for _name, data in users.items():
            if data.get("id") == user_id:
                return data
        return None

    def save_user(self, username: str, user_data: dict[str, Any]) -> None:
        users = self._read_json(self._data_dir / "users.json")
        users[username] = user_data
        self._write_json(self._data_dir / "users.json", users)

    def user_exists(self, username: str) -> bool:
        return self.get_user(username) is not None

    # работа с портфелями
    def get_portfolio(self, user_id: str) -> dict[str, Any] | None:
        portfolios = self._read_json(self._data_dir / "portfolios.json")
        return portfolios.get(user_id)

    def save_portfolio(self, user_id: str, portfolio_data: dict[str, Any]) -> None:
        portfolios = self._read_json(self._data_dir / "portfolios.json")
        portfolios[user_id] = portfolio_data
        self._write_json(self._data_dir / "portfolios.json", portfolios)

    # работа с курсами
    def get_crypto_rates(self) -> dict[str, Any]:
        return self._read_json(self._data_dir / "rates.json")

    def save_crypto_rates(self, rates: dict[str, Any]) -> None:
        self._write_json(self._data_dir / "rates.json", rates)

    def get_fiat_rates(self) -> dict[str, Any]:
        return self._read_json(self._data_dir / "exchange_rates.json")

    def save_fiat_rates(self, rates: dict[str, Any]) -> None:
        self._write_json(self._data_dir / "exchange_rates.json", rates)

    def get_rate(self, currency_code: str) -> float | None:
        code = currency_code.upper()
        crypto = self.get_crypto_rates()
        if code in crypto:
            return crypto[code].get("usd")

        fiat = self.get_fiat_rates()
        if "rates" in fiat and code in fiat["rates"]:
            rate = fiat["rates"][code]
            if rate and rate != 0:
                return 1 / rate
        return None

    @classmethod
    def reset(cls) -> None:
        """Сброс singleton, нужна для тестов."""
        cls._instance = None


def get_database(data_dir: Path | None = None) -> DatabaseManager:
    """Быстрый доступ к DatabaseManager."""
    return DatabaseManager(data_dir)
