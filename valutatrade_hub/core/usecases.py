"""Основные операции: регистрация, вход, покупка и продажа."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from valutatrade_hub.core.currencies import CurrencyRegistry
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    AuthenticationError,
    CurrencyNotFoundError,
    InsufficientFundsError,
    StaleRatesError,
    UserAlreadyExistsError,
    UserNotFoundError,
    ValidationError,
)
from valutatrade_hub.core.models import Portfolio, User
from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.database import get_database
from valutatrade_hub.infra.settings import get_settings
from valutatrade_hub.parser_service.storage import get_storage
from valutatrade_hub.parser_service.updater import run_once


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

    user_id = db.next_user_id()
    new_user = User.create_new(user_id=user_id, username=username, password=password)

    db.save_user(new_user.to_dict())

    # пустой портфель
    portfolio = Portfolio(user_id=user_id)
    db.save_portfolio(portfolio.to_dict())

    return {"success": True, "user_id": user_id, "username": username}


@log_action("LOGIN")
def login(username: str, password: str) -> dict[str, Any]:
    """Авторизация пользователя по логину и паролю."""
    db = get_database()

    user_data = db.get_user(username)
    if not user_data:
        raise UserNotFoundError(username)

    user = User.from_dict(user_data)
    if not user.verify_password(password):
        raise AuthenticationError("Неверный пароль")

    return {"success": True, "user_id": user.user_id, "username": user.username}


def show_portfolio(user_id: int, base: str = "USD") -> dict[str, Any]:
    """Возвращает портфель и его стоимость в базовой валюте."""
    db = get_database()
    storage = get_storage()

    portfolio_data = db.get_portfolio(user_id)
    if not portfolio_data:
        portfolio_data = Portfolio(user_id=user_id).to_dict()
        db.save_portfolio(portfolio_data)

    portfolio = Portfolio.from_dict(portfolio_data)
    base_currency = base.upper()

    rates = storage.get_all_rates()
    total_value = portfolio.get_total_value(rates=rates, base=base_currency)

    return {
        "success": True,
        "portfolio": portfolio.to_dict(),
        "base": base_currency,
        "total_value": total_value,
    }


@log_action("BUY")
def buy(user_id: int, currency_code: str, amount: float) -> dict[str, Any]:
    """Покупка валюты за USD (amount — количество валюты)."""
    if amount <= 0:
        raise ValidationError("'amount' должен быть положительным числом")

    code = CurrencyRegistry.get_currency(currency_code).code  # валидирует

    rate_info = get_rate(code)
    rate = rate_info["rate"]

    db = get_database()

    portfolio_data = db.get_portfolio(user_id)
    if not portfolio_data:
        portfolio_data = Portfolio(user_id=user_id).to_dict()
    portfolio = Portfolio.from_dict(portfolio_data)

    usd_wallet = portfolio.get_or_create_wallet("USD")
    cost_usd = amount * rate
    if usd_wallet.balance < cost_usd:
        raise InsufficientFundsError(available=usd_wallet.balance, required=cost_usd, code="USD")

    target_wallet = portfolio.get_or_create_wallet(code)
    usd_wallet.withdraw(cost_usd)
    target_wallet.deposit(amount)

    db.save_portfolio(portfolio.to_dict())
    # rates already in storage; no extra save

    return {
        "success": True,
        "currency_code": code,
        "amount": amount,
        "rate": rate,
        "usd_spent": cost_usd,
    }


@log_action("SELL")
def sell(user_id: int, currency_code: str, amount: float) -> dict[str, Any]:
    """Продажа валюты за USD (amount — количество валюты)."""
    if amount <= 0:
        raise ValidationError("'amount' должен быть положительным числом")

    code = CurrencyRegistry.get_currency(currency_code).code

    rate_info = get_rate(code)
    rate = rate_info["rate"]

    db = get_database()

    portfolio_data = db.get_portfolio(user_id)
    if not portfolio_data:
        raise ValidationError("Портфель не найден")
    portfolio = Portfolio.from_dict(portfolio_data)

    wallet = portfolio.get_wallet(code)
    if wallet is None or wallet.balance < amount:
        available = wallet.balance if wallet else 0.0
        raise InsufficientFundsError(available=available, required=amount, code=code)

    usd_wallet = portfolio.get_or_create_wallet("USD")
    wallet.withdraw(amount)
    revenue = amount * rate
    usd_wallet.deposit(revenue)

    db.save_portfolio(portfolio.to_dict())

    return {
        "success": True,
        "currency_code": code,
        "amount": amount,
        "rate": rate,
        "usd_received": revenue,
    }


def get_rate(from_code: str, to_code: str = "USD") -> dict[str, Any]:
    """Возвращает курс from->to (поддерживаем to=USD согласно ТЗ)."""
    from_cur = CurrencyRegistry.get_currency(from_code)
    to_code = to_code.upper()
    if to_code != "USD":
        raise ValidationError(f"Неизвестная базовая валюта '{to_code}'")

    settings = get_settings()
    ttl = settings.rates_ttl
    storage = get_storage()

    rate, updated_at = storage.get_rate_with_timestamp(from_cur.code)

    if rate is None or _is_stale(updated_at, ttl):
        # пробуем обновить кэш
        try:
            run_once()
            rate, updated_at = storage.get_rate_with_timestamp(from_cur.code)
        except Exception as exc:
            raise ApiRequestError(str(exc)) from exc

    if rate is None:
        raise CurrencyNotFoundError(from_cur.code)
    if _is_stale(updated_at, ttl):
        raise StaleRatesError(f"{from_cur.code}->{to_code}", updated_at)

    return {
        "currency_code": from_cur.code,
        "rate": rate,
        "updated_at": updated_at,
    }


def _is_stale(updated_at: str | None, ttl_seconds: int) -> bool:
    if not updated_at:
        return True
    try:
        ts = datetime.fromisoformat(updated_at)
    except ValueError:
        return True
    now = datetime.now(timezone.utc)
    delta = (now - ts).total_seconds()
    return delta > ttl_seconds


def get_all_rates() -> dict[str, float]:
    """Берёт все курсы из хранилища парсера."""
    storage = get_storage()
    return storage.get_all_rates()
