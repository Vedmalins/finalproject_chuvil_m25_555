"""Настройки приложения.

Основной источник — секция [tool.valutatrade] в pyproject.toml.
Фолбэк: config.json (если присутствует) или встроенные дефолты.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:  # Python 3.11+
    import tomllib  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    try:
        import tomli as tomllib  # type: ignore
    except ModuleNotFoundError:
        tomllib = None  # type: ignore

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config.json"
DEFAULT_PYPROJECT_PATH = Path(__file__).parent.parent.parent / "pyproject.toml"


class SettingsLoader:
    """Singleton для конфигов, чтобы загрузка была один раз."""

    _instance: SettingsLoader | None = None
    _settings: dict[str, Any] = {}
    _config_path: Path | None = None

    def __new__(cls, config_path: Path | None = None) -> SettingsLoader:  # noqa: D401
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._config_path = config_path
            cls._load_config()
        return cls._instance

    # --- загрузка ---
    @classmethod
    def _load_config(cls) -> None:
        """Читает настройки из pyproject.toml или config.json."""
        pyproject_settings = cls._read_pyproject()
        file_settings = cls._read_json_config()
        cls._settings = cls._get_defaults()
        cls._settings.update(file_settings)
        cls._settings.update(pyproject_settings)

    @classmethod
    def _read_pyproject(cls) -> dict[str, Any]:
        path = DEFAULT_PYPROJECT_PATH
        if not path.exists():
            return {}
        if tomllib is None:  # tomllib недоступен в ранних версиях python
            return {}
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return data.get("tool", {}).get("valutatrade", {}) or {}

    @classmethod
    def _read_json_config(cls) -> dict[str, Any]:
        path = cls._config_path or DEFAULT_CONFIG_PATH
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    @staticmethod
    def _get_defaults() -> dict[str, Any]:
        """Базовые настройки на случай отсутствия конфига."""
        return {
            "DATA_DIR": "data",
            "LOG_PATH": "logs/actions.log",
            "RATES_TTL_SECONDS": 300,
            "DEFAULT_BASE_CURRENCY": "USD",
        }

    # --- публичный API ---
    def get(self, key: str, default: Any = None) -> Any:
        return self._settings.get(key, default)

    @property
    def data_dir(self) -> Path:
        return Path(self.get("DATA_DIR", "data"))

    @property
    def log_path(self) -> Path:
        return Path(self.get("LOG_PATH", "logs/actions.log"))

    @property
    def rates_ttl(self) -> int:
        return int(self.get("RATES_TTL_SECONDS", 300))

    @property
    def default_base_currency(self) -> str:
        return str(self.get("DEFAULT_BASE_CURRENCY", "USD")).upper()

    @classmethod
    def reset(cls) -> None:
        cls._instance = None
        cls._settings = {}
        cls._config_path = None


def get_settings(config_path: Path | None = None) -> SettingsLoader:
    return SettingsLoader(config_path)
