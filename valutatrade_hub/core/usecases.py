"""Основные операции: регистрация, вход, покупка и продажа."""

from __future__ import annotations

from typing import Any

from valutatrade_hub.core.exceptions import (
    AuthenticationError,
    InvalidCurrencyError,
    UserAlreadyExistsError,
    UserNotFoundError,
    ValidationError,
)
from valutatrade_hub.core.utils import generate_user_id, hash_password, verify_password
from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.database import get_database


@log_action("REGISTER")
def register(username: str, password: str) -> dict[str, Any]:
    """Регистрирует нового пользователя и заводит пустой портфель."""
    db = get_database()

    if not username or not username.strip():
        raise ValidationError("Имя пользователя не может быть пустым")
    if not password:
        raise ValidationError("Пароль не может быть пустым")

    username = username.strip()

    if db.user_exists(username):
        raise UserAlreadyExistsError(username)

    user_id = generate_user_id()
    user_data = {
        "id": user_id,
        "username": username,
        "password_hash": hash_password(password),
        "created_at": None,
    }

    db.save_user(username, user_data)

    portfolio_data = {"user_id": user_id, "wallets": {"USD": 10000.0}}
    db.save_portfolio(user_id, portfolio_data)

    return {"success": True, "user_id": user_id, "username": username}


@log_action("LOGIN")
def login(username: str, password: str) -> dict[str, Any]:
    """Авторизация пользователя по логину и паролю."""
    db = get_database()

    user_data = db.get_user(username)
    if not user_data:
        raise UserNotFoundError(username)

    stored_hash = user_data.get("password_hash", "")
    if not verify_password(password, stored_hash):
        raise AuthenticationError("Неверный пароль")

    return {"success": True, "user_id": user_data["id"], "username": username}


def show_portfolio(user_id: str) -> dict[str, Any]:
    """Возвращает портфель, при отсутствии создает пустой."""
    db = get_database()

    portfolio_data = db.get_portfolio(user_id)
    if not portfolio_data:
        portfolio_data = {"user_id": user_id, "wallets": {}}
        db.save_portfolio(user_id, portfolio_data)

    return {"success": True, "portfolio": portfolio_data}


@log_action("BUY")
def buy(user_id: str, currency_code: str, usd_amount: float) -> dict[str, Any]:
    """Покупка валюты за USD по текущему курсу."""
    db = get_database()

    if usd_amount <= 0:
        raise ValidationError("Сумма должна быть больше 0")

    currency_code = currency_code.upper()
    rate = db.get_rate(currency_code)
    if not rate:
        raise InvalidCurrencyError(currency_code)

    amount = usd_amount / rate

    portfolio_data = db.get_portfolio(user_id) or {"user_id": user_id, "wallets": {}}
    wallets = portfolio_data.get("wallets", {})

    usd_balance = wallets.get("USD", 0)
    if usd_balance < usd_amount:
        raise ValidationError(f"Недостаточно USD: есть {usd_balance}, нужно {usd_amount}")

    wallets["USD"] = usd_balance - usd_amount
    wallets[currency_code] = wallets.get(currency_code, 0) + amount

    portfolio_data["wallets"] = wallets
    db.save_portfolio(user_id, portfolio_data)

    return {
        "success": True,
        "currency_code": currency_code,
        "amount": amount,
        "rate": rate,
        "usd_spent": usd_amount,
    }


@log_action("SELL")
def sell(user_id: str, currency_code: str, amount: float) -> dict[str, Any]:
    """Продажа валюты за USD."""
    db = get_database()

    if amount <= 0:
        raise ValidationError("Количество должно быть больше 0")

    currency_code = currency_code.upper()
    rate = db.get_rate(currency_code)
    if not rate:
        raise InvalidCurrencyError(currency_code)

    portfolio_data = db.get_portfolio(user_id)
    if not portfolio_data:
        raise ValidationError("Портфель не найден")

    wallets = portfolio_data.get("wallets", {})
    current = wallets.get(currency_code, 0)
    if current < amount:
        raise ValidationError(
            f"Недостаточно {currency_code}: есть {current}, нужно {amount}"
        )

    usd_received = amount * rate
    wallets[currency_code] = current - amount
    wallets["USD"] = wallets.get("USD", 0) + usd_received

    portfolio_data["wallets"] = wallets
    db.save_portfolio(user_id, portfolio_data)

    return {
        "success": True,
        "currency_code": currency_code,
        "amount": amount,
        "rate": rate,
        "usd_received": usd_received,
    }


def get_rate(currency_code: str) -> dict[str, Any]:
    """Возвращает курс валюты к USD или кидает ошибку."""
    db = get_database()

    currency_code = currency_code.upper()
    rate = db.get_rate(currency_code)
    if not rate:
        raise InvalidCurrencyError(currency_code)

    return {"currency_code": currency_code, "rate": rate}


def get_all_rates() -> dict[str, float]:
    """Берёт все курсы из хранилища парсера."""
    from valutatrade_hub.parser_service.storage import get_storage

    storage = get_storage()
    return storage.get_all_rates()
