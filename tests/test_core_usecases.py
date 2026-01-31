from __future__ import annotations

import types
from datetime import datetime, timezone
from pathlib import Path

import pytest

from valutatrade_hub.core.models import Portfolio, User
from valutatrade_hub.core.usecases import buy, login, register, sell


@pytest.fixture()
def fake_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Isolate data/log paths and singletons to a temp directory."""

    class FakeSettings:
        def __init__(self, root: Path) -> None:
            self.data_dir = root
            self.log_path = root / "actions.log"
            self.rates_ttl = 300
            self.default_base_currency = "USD"

        def get(self, key: str, default=None):
            mapping = {
                "DATA_DIR": str(self.data_dir),
                "LOG_PATH": str(self.log_path),
                "RATES_TTL_SECONDS": self.rates_ttl,
                "DEFAULT_BASE_CURRENCY": self.default_base_currency,
            }
            return mapping.get(key, default)

    fake_settings = FakeSettings(tmp_path)

    # Patch get_settings everywhere it's imported
    targets = [
        "valutatrade_hub.infra.settings.get_settings",
        "valutatrade_hub.infra.database.get_settings",
        "valutatrade_hub.logging_config.get_settings",
        "valutatrade_hub.core.usecases.get_settings",
    ]
    for target in targets:
        monkeypatch.setattr(target, lambda config_path=None, _fs=fake_settings: _fs)

    # Reset singletons and point DB to temp dir
    from valutatrade_hub.infra.database import DatabaseManager, get_database
    from valutatrade_hub.infra.settings import SettingsLoader

    DatabaseManager.reset()
    SettingsLoader.reset()
    db = get_database(tmp_path)

    yield fake_settings, db

    # teardown
    DatabaseManager.reset()
    SettingsLoader.reset()


def test_user_password_change():
    user = User.create_new(user_id=1, username="alice", password="1234")
    assert user.verify_password("1234")
    old_hash, old_salt = user._hashed_password, user._salt  # noqa: SLF001

    user.change_password("5678")
    assert user.verify_password("5678")
    assert user._hashed_password != old_hash  # noqa: SLF001
    assert user._salt != old_salt  # noqa: SLF001


def test_portfolio_total_value():
    pf = Portfolio(user_id=1)
    pf.add_currency("USD")
    pf.get_wallet("USD").deposit(100.0)
    pf.add_currency("BTC")
    pf.get_wallet("BTC").deposit(0.1)
    pf.add_currency("EUR")
    pf.get_wallet("EUR").deposit(200.0)

    rates = {"BTC_USD": 20_000.0, "EUR_USD": 1.1, "USD_USD": 1.0}
    total = pf.get_total_value(rates=rates, base="USD")

    assert total == pytest.approx(2320.0)


def test_register_login_buy_sell_flow(fake_env, monkeypatch: pytest.MonkeyPatch):
    _, db = fake_env

    # avoid real network in get_rate refresh
    monkeypatch.setattr("valutatrade_hub.core.usecases.run_once", lambda source=None: {"ok": True})

    timestamp = datetime.now(timezone.utc).isoformat()
    db.save_rates_cache(
        {
            "pairs": {
                "BTC_USD": {"rate": 20_000.0, "updated_at": timestamp, "source": "CoinGecko"},
                "USD_USD": {"rate": 1.0, "updated_at": timestamp, "source": "ExchangeRate-API"},
            },
            "last_refresh": timestamp,
        }
    )

    reg = register("bob", "1234")
    user_id = reg["user_id"]

    # add starting USD balance
    portfolio_data = db.get_portfolio(user_id)
    pf = Portfolio.from_dict(portfolio_data)
    pf.get_or_create_wallet("USD").deposit(1_000.0)
    db.save_portfolio(pf.to_dict())

    login_res = login("bob", "1234")
    assert login_res["user_id"] == user_id

    buy_res = buy(user_id, "BTC", 0.02)
    assert buy_res["usd_spent"] == pytest.approx(400.0)

    pf_after_buy = Portfolio.from_dict(db.get_portfolio(user_id))
    assert pf_after_buy.get_wallet("BTC").balance == pytest.approx(0.02)
    assert pf_after_buy.get_wallet("USD").balance == pytest.approx(600.0)

    sell_res = sell(user_id, "BTC", 0.01)
    assert sell_res["usd_received"] == pytest.approx(200.0)

    pf_after_sell = Portfolio.from_dict(db.get_portfolio(user_id))
    assert pf_after_sell.get_wallet("BTC").balance == pytest.approx(0.01)
    assert pf_after_sell.get_wallet("USD").balance == pytest.approx(800.0)
