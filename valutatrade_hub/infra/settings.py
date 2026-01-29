"""Настройки приложения, храним в одном месте чтобы не путаться."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config.json"


class SettingsLoader:
    """Singleton для конфигов, чтобы загрузка была один раз."""

    _instance: "SettingsLoader | None" = None
    _settings: dict[str, Any] = {}
    _config_path: Path | None = None

    def __new__(cls, config_path: Path | None = None) -> "SettingsLoader":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._config_path = config_path or DEFAULT_CONFIG_PATH
            cls._load_config()
        return cls._instance

    @classmethod
    def _load_config(cls) -> None:
        """Читает конфиг из файла или берет дефолты."""
        if cls._config_path and cls._config_path.exists():
            with open(cls._config_path, encoding="utf-8") as f:
                cls._settings = json.load(f)
        else:
            cls._settings = cls._get_defaults()

    @classmethod
    def _get_defaults(cls) -> dict[str, Any]:
        """Базовые настройки на случай отсутствия конфига."""
        return {
            "data_dir": "data",
            "log_dir": "logs",
            "log_level": "INFO",
            "rates_ttl_seconds": 300,
            "api": {
                "coingecko_url": "https://api.coingecko.com/api/v3",
                "exchangerate_url": "https://api.exchangerate-api.com/v4/latest",
            },
            "update_interval_seconds": 60,
            "default_currency": "USD",
            "supported_fiat": ["USD", "EUR", "RUB", "GBP"],
            "supported_crypto": ["BTC", "ETH", "USDT"],
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Возвращает настройку по ключу."""
        return self._settings.get(key, default)

    def get_nested(self, *keys: str, default: Any = None) -> Any:
        """Достает вложенное значение типа api -> url."""
        value: Any = self._settings
        for key in keys:
            if not isinstance(value, dict):
                return default
            value = value.get(key)
            if value is None:
                return default
        return value

    @property
    def data_dir(self) -> Path:
        """Каталог для данных."""
        return Path(self.get("data_dir", "data"))

    @property
    def log_dir(self) -> Path:
        """Каталог для логов."""
        return Path(self.get("log_dir", "logs"))

    @property
    def log_path(self) -> Path:
        """Путь к файлу логов."""
        return self.log_dir / "app.log"

    @property
    def log_level(self) -> str:
        """Уровень логирования."""
        return self.get("log_level", "INFO")

    @classmethod
    def reset(cls) -> None:
        """Сброс singleton, используется в тестах."""
        cls._instance = None
        cls._settings = {}
        cls._config_path = None


def get_settings(config_path: Path | None = None) -> SettingsLoader:
    """Удобный доступ к настройкам."""
    return SettingsLoader(config_path)
