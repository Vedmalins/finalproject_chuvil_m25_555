"""Всякие утилиты под рукой, чтобы не плодить дубли."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def read_json(path: str | Path) -> Any:
    """Читаю json из файла, если пусто возвращаю пустой словарь."""
    file = Path(path)
    if not file.exists():
        return {}
    text = file.read_text(encoding="utf-8")
    if not text.strip():
        return {}
    return json.loads(text)


def write_json(path: str | Path, data: Any) -> None:
    """Сохраняю json красиво с отступами."""
    file = Path(path)
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def generate_id(existing: list[int] | None = None) -> int:
    """Простой генератор id: берем макс и плюс один."""
    if not existing:
        return 1
    return max(existing) + 1


def now_iso() -> str:
    """Текущее время в isoформате."""
    return datetime.utcnow().isoformat()
