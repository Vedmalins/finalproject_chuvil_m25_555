# finalproject_chuvil_m25_555

Мини-приложение «ValutaTrade Hub»: симулятор валютного кошелька с CLI, парсером курсов и файловым хранилищем.

## Как запустить
```bash
make install      # poetry install (нужен Poetry)
make project      # запуск CLI: poetry run project
make lint         # ruff check .
make test         # python -m pytest (вручную, если нужно)
```
Альтернатива без make:
```bash
poetry install
poetry run project
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

## Основные команды CLI
- `register` — регистрация пользователя.
- `login` — вход.
- `rates` — показать все курсы из локального кэша.
- `rate <CODE>` — курс конкретной валюты.
- `update` — обновить курсы (Parser Service: CoinGecko + ExchangeRate).
- `portfolio` — показать портфель (после login).
- `buy <CODE> <USD>` — купить валюту.
- `sell <CODE> <AMOUNT>` — продать валюту.
- `logout`, `exit`, `help`.

## Parser Service
- Конфиг: `parser_service/config.py` (URL, таймаут, поддерживаемые валюты).
- Клиенты: `api_clients.py` (CoinGecko, ExchangeRate).
- Обновление: `updater.py` (`run_once`) и `scheduler.py` (фоновые циклы).
- Хранилище курсов: `storage.py` (работает через `infra/database.py`).

## Данные и логи
- Все данные — в `data/*.json`.
- Файлы в каталоге `data/` инициализируются пустыми структурами и обновляются приложением и сервисом парсинга автоматически; вручную их править не нужно.
- Логи — путь задаётся в `[tool.valutatrade] LOG_PATH` (по умолчанию `logs/actions.log`), ротация настроена в `logging_config.py`.

## Тесты и стиль
- Юнит-тесты: `python -m pytest` (или `poetry run pytest`).
- Линтер: `ruff check .` (цель `make lint`).

## Демо (asciinema/GIF)
- Деморолик будет добавлен позже; сценарий: register → login → rates → update → buy/sell → portfolio → rate.
