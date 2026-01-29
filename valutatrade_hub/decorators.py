"""Декораторы: сейчас только логирование действий."""

from __future__ import annotations

import functools
from collections.abc import Callable
from datetime import datetime
from typing import Any, TypeVar

from valutatrade_hub.logging_config import get_logger

F = TypeVar("F", bound=Callable[..., Any])


def log_action(action: str, verbose: bool = False) -> Callable[[F], F]:
    """Логирует вызовы функций, пишет что и когда делалось."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = get_logger("actions")
            timestamp = datetime.utcnow().isoformat() + "Z"

            log_data = {"timestamp": timestamp, "action": action, "function": func.__name__}
            _extract_params(log_data, kwargs, args, func)

            if verbose:
                logger.debug(f"Старт {action}: {log_data}")

            try:
                result = func(*args, **kwargs)

                if isinstance(result, dict):
                    if "user_id" in result and "user_id" not in log_data:
                        log_data["user_id"] = result["user_id"]
                    if "rate" in result:
                        log_data["rate"] = result["rate"]
                    if "currency_code" in result:
                        log_data["currency_code"] = result["currency_code"]

                log_data["result"] = "OK"
                logger.info(_format_log_message(log_data))

                if verbose:
                    logger.debug(f"Готово {action}: {log_data}")

                return result

            except Exception as e:
                log_data["result"] = "ERROR"
                log_data["error_type"] = type(e).__name__
                log_data["error_message"] = str(e)
                logger.warning(_format_log_message(log_data))

                if verbose:
                    logger.debug(f"Ошибка {action}: {log_data}", exc_info=True)

                raise

        return wrapper  # type: ignore

    return decorator


def _extract_params(
    log_data: dict[str, Any],
    kwargs: dict[str, Any],
    args: tuple,
    func: Callable,
) -> None:
    """Достаёт интересные параметры из args и kwargs."""
    for key in ("username", "user_id", "currency_code", "amount"):
        if key in kwargs:
            log_data[key] = kwargs[key]

    try:
        import inspect

        sig = inspect.signature(func)
        params = list(sig.parameters.keys())
        for i, arg in enumerate(args):
            if i < len(params):
                name = params[i]
                if name in ("username", "user_id", "currency_code", "amount"):
                    log_data[name] = arg
    except Exception:
        pass


def _format_log_message(data: dict[str, Any]) -> str:
    """Собирает строку для логов."""
    parts = []
    for key, value in data.items():
        if isinstance(value, str) and " " in value:
            parts.append(f'{key}="{value}"')
        else:
            parts.append(f"{key}={value}")
    return " | ".join(parts)
