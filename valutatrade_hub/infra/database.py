"""Простейшая база на json, лежит рядом с данными."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from valutatrade_hub.infra.settings import get_settings


class DatabaseManager:
    """Singleton для работы с файлами users/portfolios/rates."""

    _instance: DatabaseManager | None = None
    _data_dir: Path

    def __new__(cls, data_dir: Path | None = None) -> DatabaseManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            settings = get_settings()
            cls._data_dir = data_dir or settings.data_dir
            cls._data_dir.mkdir(parents=True, exist_ok=True)
            cls._instance._init_files()
        return cls._instance

    # --- базовые IO ---
    def _init_files(self) -> None:
        """Создает пустые json если их нет."""
        defaults: dict[str, Any] = {
            "users.json": [],
            "portfolios.json": [],
            "rates.json": {"pairs": {}, "last_refresh": None},
            "exchange_rates.json": [],
        }
        for name, content in defaults.items():
            path = self._data_dir / name
            if not path.exists():
                self._write_json(path, content)

    @staticmethod
    def _read_json(path: Path) -> Any:
        """Чтение json, при ошибке отдает пустую структуру по умолчанию."""
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            if path.stem in ("users", "portfolios", "exchange_rates"):
                return []
            return {}

    @staticmethod
    def _write_json(path: Path, data: Any) -> None:
        """Запись json через временный файл чтобы не потерять данные."""
        temp = path.with_suffix(".tmp")
        with open(temp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(temp, path)

    # --- пользователи ---
    def _load_users(self) -> list[dict[str, Any]]:
        raw = self._read_json(self._data_dir / "users.json")
        if isinstance(raw, dict):
            return list(raw.values())
        return raw or []

    def _save_users(self, users: list[dict[str, Any]]) -> None:
        self._write_json(self._data_dir / "users.json", users)

    def user_exists(self, username: str) -> bool:
        return self.get_user(username) is not None

    def get_user(self, username: str) -> dict[str, Any] | None:
        for user in self._load_users():
            if user.get("username") == username:
                return user
        return None

    def get_user_by_id(self, user_id: int) -> dict[str, Any] | None:
        for user in self._load_users():
            if user.get("user_id") == user_id:
                return user
        return None

    def next_user_id(self) -> int:
        users = self._load_users()
        ids = [u.get("user_id") for u in users if isinstance(u.get("user_id"), int)]
        if not ids:
            return 1
        return max(ids) + 1

    def save_user(self, user_data: dict[str, Any]) -> None:
        users = self._load_users()
        # обновление если username уже есть
        updated = False
        for idx, user in enumerate(users):
            if user.get("username") == user_data.get("username"):
                users[idx] = user_data
                updated = True
                break
        if not updated:
            users.append(user_data)
        self._save_users(users)

    # --- портфели ---
    def _load_portfolios(self) -> list[dict[str, Any]]:
        raw = self._read_json(self._data_dir / "portfolios.json")
        if isinstance(raw, dict):
            return list(raw.values())
        return raw or []

    def _save_portfolios(self, portfolios: list[dict[str, Any]]) -> None:
        self._write_json(self._data_dir / "portfolios.json", portfolios)

    def get_portfolio(self, user_id: int) -> dict[str, Any] | None:
        for pf in self._load_portfolios():
            if pf.get("user_id") == user_id:
                return pf
        return None

    def save_portfolio(self, portfolio_data: dict[str, Any]) -> None:
        portfolios = self._load_portfolios()
        updated = False
        for idx, pf in enumerate(portfolios):
            if pf.get("user_id") == portfolio_data.get("user_id"):
                portfolios[idx] = portfolio_data
                updated = True
                break
        if not updated:
            portfolios.append(portfolio_data)
        self._save_portfolios(portfolios)

    # --- кэш курсов ---
    def get_rates_cache(self) -> dict[str, Any]:
        """Текущее объединённое состояние курсов."""
        data = self._read_json(self._data_dir / "rates.json")
        return data if isinstance(data, dict) else {"pairs": {}, "last_refresh": None}

    def save_rates_cache(self, cache: dict[str, Any]) -> None:
        """Сохраняет объединённый кэш курсов."""
        self._write_json(self._data_dir / "rates.json", cache)

    # --- история курсов ---
    def append_history_record(self, record: dict[str, Any]) -> None:
        """Добавляет запись в exchange_rates.json (история)."""
        history_path = self._data_dir / "exchange_rates.json"
        history = self._read_json(history_path)
        if not isinstance(history, list):
            history = []
        history.append(record)
        self._write_json(history_path, history)

    # --- утилиты ставок (обратная совместимость) ---
    def get_rate(self, currency_code: str) -> float | None:
        """Получает курс code->USD если есть в кэше."""
        cache = self.get_rates_cache()
        pairs = cache.get("pairs", {})
        key = f"{currency_code.upper()}_USD"
        entry = pairs.get(key)
        if entry:
            return entry.get("rate")
        # попробовать обратный ключ USD_CODE
        reverse = f"USD_{currency_code.upper()}"
        entry = pairs.get(reverse)
        if entry and entry.get("rate"):
            rate = entry.get("rate")
            if rate:
                return 1 / rate
        return None

    @classmethod
    def reset(cls) -> None:
        """Сброс singleton, нужна для тестов."""
        cls._instance = None


def get_database(data_dir: Path | None = None) -> DatabaseManager:
    """Быстрый доступ к DatabaseManager."""
    return DatabaseManager(data_dir)
