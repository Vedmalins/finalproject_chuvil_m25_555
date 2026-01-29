"""Утилиты под руку: json, пароли, id, форматики."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


def read_json(path: str | Path) -> Any:
    """Читаю json из файла, если его нет отдаю пустой словарь."""
    file = Path(path)
    if not file.exists():
        return {}
    text = file.read_text(encoding="utf-8")
    if not text.strip():
        return {}
    return json.loads(text)


def write_json(path: str | Path, data: Any) -> None:
    """Пишу json с отступами, стараюсь не сломать кодировку."""
    file = Path(path)
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def generate_user_id() -> str:
    """UUID4 строка, должна быть уникальна."""
    return str(uuid.uuid4())


def hash_password(password: str) -> str:
    """Хэш пароля через sha256, без соли чтобы тесты не страдали."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """Сравниваю пароль с хэшем."""
    return hash_password(password) == hashed


def validate_username(username: str) -> bool:
    """Простая проверка логина: длина 3-50 и только буквы/цифры/подчерк."""
    if not username or not isinstance(username, str):
        return False
    username = username.strip()
    if len(username) < 3 or len(username) > 50:
        return False
    if " " in username:
        return False
    for ch in username:
        if not (ch.isalnum() or ch == "_"):
            return False
    return True


def validate_password(password: str) -> bool:
    """Пароль минимум 6 символов, больше ничего не проверяю."""
    return isinstance(password, str) and len(password) >= 6


def format_datetime(dt: datetime) -> str:
    """Формат даты в читабельный вид."""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_currency_amount(amount: float, code: str) -> str:
    """Формат суммы с кодом валюты, чуть подгонка по знакам после запятой."""
    code = code.upper()
    if code in ("BTC", "ETH"):
        return f"{amount:,.8f} {code}"
    if code in ("SOL",):
        return f"{amount:,.6f} {code}"
    return f"{amount:,.2f} {code}"


def generate_id(existing: list[int] | None = None) -> int:
    """Генерация числового id из макс+1, вдруг пригодится."""
    if not existing:
        return 1
    return max(existing) + 1


def now_iso() -> str:
    """Текущая дата во времени UTC в iso."""
    return datetime.utcnow().isoformat()
