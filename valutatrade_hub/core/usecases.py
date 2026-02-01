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

    # валидируем базовую валюту
    base_currency = CurrencyRegistry.get_currency(base).code

    portfolio_data = db.get_portfolio(user_id)
    if not portfolio_data:
        portfolio_data = Portfolio(user_id=user_id).to_dict()
        db.save_portfolio(portfolio_data)

    portfolio = Portfolio.from_dict(portfolio_data)

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

    code = CurrencyRegistry.get_currency(currency_code).code

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
    before = target_wallet.balance
    usd_wallet.withdraw(cost_usd)
    target_wallet.deposit(amount)
    after = target_wallet.balance

    db.save_portfolio(portfolio.to_dict())

    return {
        "success": True,
        "currency_code": code,
        "amount": amount,
        "rate": rate,
        "usd_spent": cost_usd,
        "before": before,
        "after": after,
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
    if wallet is None:
        raise ValidationError(
            f"У вас нет кошелька '{code}'. Добавьте валюту: она создаётся автоматически при первой покупке."
        )
    if wallet.balance < amount:
        raise InsufficientFundsError(available=wallet.balance, required=amount, code=code)

    usd_wallet = portfolio.get_or_create_wallet("USD")
    before = wallet.balance
    wallet.withdraw(amount)
    revenue = amount * rate
    usd_wallet.deposit(revenue)
    after = wallet.balance

    db.save_portfolio(portfolio.to_dict())

    return {
        "success": True,
        "currency_code": code,
        "amount": amount,
        "rate": rate,
        "usd_received": revenue,
        "before": before,
        "after": after,
    }


def get_rate(from_code: str, to_code: str = "USD") -> dict[str, Any]:
    """Возвращает курс from->to, поддерживает любые коды из реестра."""
    from_cur = CurrencyRegistry.get_currency(from_code)
    to_cur = CurrencyRegistry.get_currency(to_code)

    settings = get_settings()
    ttl = settings.rates_ttl
    storage = get_storage()

    pair_direct = f"{from_cur.code}_{to_cur.code}"
    pair_reverse = f"{to_cur.code}_{from_cur.code}"

    rate = None
    updated_at = None

    cache = storage.db.get_rates_cache()
    pairs = cache.get("pairs", {})
    if pair_direct in pairs:
        rate = pairs[pair_direct].get("rate")
        updated_at = pairs[pair_direct].get("updated_at") or cache.get("last_refresh")
    elif pair_reverse in pairs and pairs[pair_reverse].get("rate"):
        rev_rate = pairs[pair_reverse]["rate"]
        rate = 1 / rev_rate if rev_rate else None
        updated_at = pairs[pair_reverse].get("updated_at") or cache.get("last_refresh")

    if rate is None or _is_stale(updated_at, ttl):
        try:
            run_once()
            cache = storage.db.get_rates_cache()
            pairs = cache.get("pairs", {})
            if pair_direct in pairs:
                rate = pairs[pair_direct].get("rate")
                updated_at = pairs[pair_direct].get("updated_at") or cache.get("last_refresh")
            elif pair_reverse in pairs and pairs[pair_reverse].get("rate"):
                rev_rate = pairs[pair_reverse]["rate"]
                rate = 1 / rev_rate if rev_rate else None
                updated_at = pairs[pair_reverse].get("updated_at") or cache.get("last_refresh")
        except Exception as exc:
            raise ApiRequestError(str(exc)) from exc

    if rate is None:
        raise CurrencyNotFoundError(f"{from_cur.code}->{to_cur.code}")
    if _is_stale(updated_at, ttl):
        raise StaleRatesError(f"{from_cur.code}->{to_cur.code}", updated_at)

    return {
        "currency_code": from_cur.code,
        "to_currency": to_cur.code,
        "rate": rate,
        "updated_at": updated_at,
    }


def _is_stale(updated_at: str | None, ttl_seconds: int) -> bool:
    """True если updated_at пустой/битый/старее ttl.

    Поддерживает ISO-строки как с '+00:00', так и с суффиксом 'Z'.
    """
    if not updated_at:
        return True

    value = updated_at.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    try:
        ts = datetime.fromisoformat(value)
    except ValueError:
        return True

    # если вдруг пришло без tzinfo, то UTC
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    return (now - ts.astimezone(timezone.utc)).total_seconds() > ttl_seconds



def get_all_rates() -> dict[str, float]:
    """Берёт все курсы из хранилища парсера."""
    storage = get_storage()
    return storage.get_all_rates()
