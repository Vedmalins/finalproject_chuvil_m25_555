# finalproject_chuvil_m25_555

Мини-приложение «ValutaTrade Hub»: симулятор валютного кошелька с CLI, парсером курсов и файловым хранилищем.

## Как запустить
```bash
make install        # poetry install (нужен Poetry)
make project        # старт CLI (poetry run project)
make lint           # ruff check .
make test           # pytest
make build          # poetry build
make publish        # poetry publish --dry-run
make package-install# python -m pip install dist/*.whl
```

## Структура
```
finalproject_chuvil_m25_555/
├── data/
│   ├── users.json
│   ├── portfolios.json
│   ├── rates.json
│   └── exchange_rates.json
├── valutatrade_hub/
│   ├── logging_config.py
│   ├── decorators.py
│   ├── core/
│   │   ├── currencies.py
│   │   ├── exceptions.py
│   │   ├── models.py
│   │   ├── usecases.py
│   │   └── utils.py
│   ├── infra/
│   │   ├── settings.py
│   │   └── database.py
│   ├── parser_service/
│   │   ├── config.py
│   │   ├── api_clients.py
│   │   ├── updater.py
│   │   ├── storage.py
│   │   └── scheduler.py
│   └── cli/
│       └── interface.py
├── main.py
├── Makefile
├── pyproject.toml
└── poetry.lock
```

## Основные команды CLI (пример сценария)
- `register --username alice --password 1234` — регистрация (пароль ≥4).
- `login --username alice --password 1234` — вход.
- `update-rates` — обновить курсы (CoinGecko + ExchangeRate-API).
- `get-rate --from BTC --to USD` — курс валюты (кэш + автообновление при просрочке TTL).
- `rates` / `show-rates` — вывести все пары из локального кэша.
- `buy --currency BTC --amount 0.05` — покупка валюты (amount в штуках, списание USD по курсу).
- `sell --currency BTC --amount 0.01` — продажа валюты, зачисление USD.
- `show-portfolio --base USD` — показать кошельки и стоимость в базовой валюте.
- `logout`, `help`, `exit`.

## Parser Service
- Конфиг: `parser_service/config.py` (URL, таймаут, списки валют, CRYPTO_ID_MAP).
- Ключ ExchangeRate-API берётся из переменной окружения `EXCHANGERATE_API_KEY` (можно положить в `.env`).
- Обновление: `updater.py` (`run_once`) + `scheduler.py` (периодический запуск).
- Хранилище: `storage.py` → `data/rates.json` (снимок) и `data/exchange_rates.json` (история).

## Данные и логи
- Все данные лежат в `data/`:
  - `users.json` — список пользователей `{user_id, username, hashed_password, salt, registration_date}`.
  - `portfolios.json` — список портфелей `{user_id, wallets: {CODE: {currency_code, balance}}}`.
  - `rates.json` — текущий кэш `pairs {CODE_BASE: {rate, updated_at, source}}, last_refresh`.
  - `exchange_rates.json` — история измерений с уникальными `id=<FROM>_<TO>_<timestamp>`.
- TTL кэша задаётся в `[tool.valutatrade] RATES_TTL_SECONDS` (pyproject.toml, по умолчанию 300 с).
- Логи пишутся в `LOG_PATH` (по умолчанию `logs/actions.log`), ротация настроена в `logging_config.py`.

## Тесты и стиль
- Юнит-тесты: `python -m pytest` (или `poetry run pytest`).
- Линтер: `ruff check .` (цель `make lint`).

## Демо (asciinema/GIF)
- Деморолик будет добавлен позже; сценарий: register → login → rates → update → buy/sell → portfolio → rate.
