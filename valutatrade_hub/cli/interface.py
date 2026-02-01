"""Простой CLI для работы с кошельком, без лишних украшений."""

from __future__ import annotations

import getpass
import shlex
from typing import Any

from prettytable import PrettyTable

from valutatrade_hub.core.currencies import CurrencyRegistry
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    AuthenticationError,
    CurrencyNotFoundError,
    InsufficientFundsError,
    InvalidCurrencyError,
    StaleRatesError,
    UserAlreadyExistsError,
    UserNotFoundError,
    ValidationError,
)
from valutatrade_hub.core.usecases import (
    buy,
    get_all_rates,
    get_rate,
    login,
    register,
    sell,
    show_portfolio,
)
from valutatrade_hub.logging_config import get_logger, setup_logging
from valutatrade_hub.parser_service.updater import run_once


class TradingCLI:
    """Держит команды и текущую сессию."""

    def __init__(self) -> None:
        setup_logging()
        self.logger = get_logger("cli")
        self.current_user: dict[str, Any] | None = None
        self.running = True
        self.public_cmds = {
            "help": self._cmd_help,
            "exit": self._cmd_exit,
            "quit": self._cmd_exit,
            "register": self._cmd_register,
            "login": self._cmd_login,
            # курсы, расширенная версия с фильтрами
            "rates": self._cmd_show_rates,
            "show-rates": self._cmd_show_rates,
            "showrates": self._cmd_show_rates,
            "rate": self._cmd_rate,
            "get-rate": self._cmd_rate,
            "update": self._cmd_update,
            "update-rates": self._cmd_update,
        }

        self.auth_cmds = {
            "portfolio": self._cmd_portfolio,
            "show-portfolio": self._cmd_portfolio,
            "buy": self._cmd_buy,
            "sell": self._cmd_sell,
           "logout": self._cmd_logout,
        }


    def run(self) -> None:
        """Основной цикл ввода."""
        self._print_welcome()
        while self.running:
            try:
                cmd = self._get_input()
                self._process(cmd)
            except KeyboardInterrupt:
                print()
                self._cmd_exit()
            except Exception as exc:
                self.logger.error(f"неожиданная ошибка: {exc}")
                print(f"Ошибка: {exc}")

    # утилиты ввода-вывода

    def _print_welcome(self) -> None:
        """Мини-баннер при старте."""
        print("=" * 40)
        print(" finalproject_chuvil_m25_555 ")
        print("=" * 40)
        print("введите help чтобы увидеть команды\n")

    def _get_input(self) -> str:
        """Читает строку, учитывает кто залогинен."""
        prompt = f"[{self.current_user.get('username')}] > " if self.current_user else "> "
        try:
            return input(prompt).strip()
        except EOFError:
            return "exit"

    def _process(self, command: str) -> None:
        """Разбирает строку на команду и args."""
        if not command:
            return
        try:
            parts = shlex.split(command)
        except ValueError as exc:
            print(f"Ошибка парсинга: {exc}")
            return
        if not parts:
            return
        name, args = parts[0].lower(), parts[1:]
        if name in self.public_cmds:
            self.public_cmds[name](args)
        elif name in self.auth_cmds:
            if self.current_user:
                self.auth_cmds[name](args)
            else:
                print("Сначала login или register, иначе никак")
        else:
            print("Команда не найдена, help поможет")

    @staticmethod
    def _get_flag(args: list[str], flag: str) -> str | None:
        """Достает значение флага из списка аргументов."""
        if flag in args:
            idx = args.index(flag)
            if idx + 1 < len(args):
                return args[idx + 1]
        for item in args:
            if item.startswith(flag + "="):
                return item.split("=", 1)[1]
        return None

    @staticmethod
    def _convert_to_base(code: str, amount: float, base: str, rates: dict[str, float]) -> float:
        """Переводит amount к базовой валюте используя пары из кэша."""
        code = code.upper()
        base = base.upper()
        if code == base:
            return amount
        pair_direct = f"{code}_{base}"
        if pair_direct in rates:
            return amount * rates[pair_direct]
        pair_code_usd = f"{code}_USD"
        pair_base_usd = f"{base}_USD"
        if pair_code_usd in rates and pair_base_usd in rates and rates[pair_base_usd] != 0:
            # amount * (code->USD) / (base->USD)
            return amount * rates[pair_code_usd] / rates[pair_base_usd]
        return 0.0

    # команды общие

    def _cmd_help(self, args: list[str]) -> None:
        """Печатает список команд."""
        print("\nОбщие команды:")
        print("  help          показать подсказку")
        print("  exit|quit     выход")
        print("  register --username <u> --password <p>   регистрация")
        print("  login --username <u> --password <p>      вход")
        print("  rates|show-rates [--currency CODE] [--top N] [--base USD]   курсы из кеша")
        print("  get-rate --from <CODE> --to USD          курс валюты (алиас rate <CODE>)")
        print("  update|update-rates       обновить курсы\n")

        if self.current_user:
            print("Команды после входа:")
            print("  portfolio|show-portfolio [--base USD]   показать кошельки")
            print("  buy --currency <код> --amount <qty>     купить валюту")
            print("  sell --currency <код> --amount <qty>    продать валюту")
            print("  logout        выйти из аккаунта\n")

    def _cmd_exit(self, args: list[str] | None = None) -> None:
        """Завершает цикл."""
        print("До встречи")
        self.running = False

    def _cmd_register(self, args: list[str]) -> None:
        """Регистрация нового пользователя."""
        username = self._get_flag(args, "--username")
        password = self._get_flag(args, "--password")

        # фолбэк на интерактив
        if not username:
            username = input("Имя: ").strip()
        if not password:
            pwd1 = getpass.getpass("Пароль: ")
            pwd2 = getpass.getpass("Повтор: ")
            if pwd1 != pwd2:
                print("Пароли разные")
                return
            password = pwd1
        try:
            result = register(username, password)
            print(
                f"Пользователь '{username}' зарегистрирован (id={result['user_id']}). "
                f"Войдите: login --username {username} --password ****"
            )
        except UserAlreadyExistsError as exc:
            print(f"Ошибка: {exc}")
        except ValidationError as exc:
            print(f"Ошибка: {exc}")

    def _cmd_login(self, args: list[str]) -> None:
        """Вход в систему."""
        if self.current_user:
            print("Уже вошли, сначала logout")
            return
        username = self._get_flag(args, "--username") or input("Имя: ").strip()
        password = self._get_flag(args, "--password") or getpass.getpass("Пароль: ")
        try:
            data = login(username, password)
            self.current_user = {"user_id": data["user_id"], "username": data["username"]}
            print(f"Вы вошли как '{username}'")
        except (AuthenticationError, UserNotFoundError) as exc:
            print(f"Ошибка: {exc}")

    def _cmd_rates(self, args: list[str]) -> None:
        """Показывает таблицу курсов из кеша (без обновления)."""
        rates = get_all_rates()
        if not rates:
            print("Курсы пустые, выполните update-rates")
            return
        # попытка вывести last_refresh если есть в кэше
        try:
            from valutatrade_hub.infra.database import get_database

            cache = get_database().get_rates_cache()
            last_refresh = cache.get("last_refresh")
            if last_refresh:
                print(f"Rates from cache (updated at {last_refresh}):")
        except Exception:
            pass
        table = PrettyTable()
        table.field_names = ["Пара", "Курс"]
        table.align["Пара"] = "l"
        table.align["Курс"] = "r"
        for pair, rate in sorted(rates.items()):
            table.add_row([pair, f"{rate:,.6f}"])
        print(table)

    def _cmd_rate(self, args: list[str]) -> None:
        """Показывает курс валюты.

        Поддержка:
        - rate <CODE>                      (старый формат)
        - get-rate --from <FROM> --to <TO> (формат из ТЗ, частично: пока только USD)
        """
        if not args:
            print("usage: rate <CODE>  |  get-rate --from <FROM> --to <TO>")
            return

        from_code = self._get_flag(args, "--from")
        to_code = self._get_flag(args, "--to") or "USD"

        # старый формат rate <CODE>
        if not from_code and len(args) == 1 and not args[0].startswith("--"):
            from_code = args[0]

        if not from_code:
            print("usage: get-rate --from <FROM> --to <TO>")
            return

        try:
            res = get_rate(from_code.upper(), to_code.upper())
            rate = res["rate"]
            updated_at = res.get("updated_at", "n/a")
            print(f"Курс {from_code.upper()}→{to_code.upper()}: {rate:,.6f} (обновлено: {updated_at})")
            if rate != 0:
                print(f"Обратный курс {to_code.upper()}→{from_code.upper()}: {1/rate:,.6f}")
        except (InvalidCurrencyError, StaleRatesError, ValidationError, CurrencyNotFoundError, ApiRequestError) as exc:
            print(f"Ошибка: {exc}")

    def _cmd_update(self, args: list[str]) -> None:
        """Тянет свежие курсы из сетки."""
        print("Обновляю курсы, секундочку...")
        source = self._get_flag(args, "--source")
        if source and source not in {"coingecko", "exchangerate"}:
            print("Неизвестный источник. Используйте coingecko или exchangerate.")
            return

        try:
            result = run_once(source=source)
        except Exception as exc:
            self.logger.error(f"update fail: {exc}")
            print(f"Ошибка обновления: {exc}")
            return

        warnings = []
        if isinstance(result, dict):
            warnings = result.get("warnings", []) or []
            updated_pairs = result.get("updated_pairs")
            last_refresh = result.get("last_refresh")

        for w in warnings:
            print(f"NOTE: {w}")

        if isinstance(result, dict):
            summary = f"Обновлено пар: {updated_pairs}"
            if last_refresh:
                summary += f", last_refresh: {last_refresh}"
            print(summary)
        print("Готово")


    def _cmd_show_rates(self, args: list[str]) -> None:
        """Показывает курсы из кеша с фильтрами."""
        currency_filter = self._get_flag(args, "--currency")
        top_raw = self._get_flag(args, "--top")
        base = self._get_flag(args, "--base") or "USD"
        rates = get_all_rates()
        if not rates:
            print("Локальный кеш курсов пуст. Выполните 'update-rates'.")
            return

        if currency_filter:
            currency_filter = currency_filter.upper()
            rates = {k: v for k, v in rates.items() if k.startswith(f"{currency_filter}_")}
            if not rates:
                print(f"Курс для '{currency_filter}' не найден в кеше.")
                return

        if base.upper() != "USD":
            # простая переконвертация через USD, если есть оба курса
            converted: dict[str, float] = {}
            for pair, rate in rates.items():
                code, pair_base = pair.split("_", 1)
                if pair_base != "USD":
                    continue
                base_pair = f"{base.upper()}_USD"
                if base_pair in rates and rates[base_pair] != 0:
                    converted[f"{code}_{base.upper()}"] = rate / rates[base_pair]
            rates = converted or rates

        sorted_items = sorted(rates.items(), key=lambda kv: kv[0])
        if top_raw:
            try:
                top_n = int(top_raw)
                crypto_codes = {c.code for c in CurrencyRegistry.list_crypto_currencies()}
                sorted_items = [
                    item for item in sorted_items if item[0].split("_", 1)[0] in crypto_codes
                ]
                sorted_items = sorted(sorted_items, key=lambda kv: kv[1], reverse=True)[:top_n]
            except ValueError:
                print("Флаг --top должен быть целым числом")
                return

        table = PrettyTable()
        table.field_names = ["Пара", "Курс"]
        table.align["Пара"] = "l"
        table.align["Курс"] = "r"
        for pair, rate in sorted_items:
            table.add_row([pair, f"{rate:,.6f}"])
        print(table)


    def _cmd_logout(self, args: list[str]) -> None:
        """Выход из аккаунта."""
        self.current_user = None
        print("Вышли из аккаунта")

    def _cmd_portfolio(self, args: list[str]) -> None:
        """Показывает баланс по валютам."""
        base = self._get_flag(args, "--base") or "USD"
        try:
            result = show_portfolio(self.current_user["user_id"], base)
        except CurrencyNotFoundError as exc:
            print(f"Ошибка: {exc}")
            return
        wallets = result.get("portfolio", {}).get("wallets", {})
        if not wallets:
            print("Портфель пуст, купите что-нибудь")
            return

        rates = get_all_rates()
        table = PrettyTable()
        table.field_names = [f"Валюта (база: {base.upper()})", "Баланс", f"В {base.upper()}"]
        table.align[table.field_names[0]] = "l"
        table.align["Баланс"] = "r"
        table.align[f"В {base.upper()}"] = "r"

        total = 0.0
        for code, raw in wallets.items():
            amount = raw.get("balance") if isinstance(raw, dict) else raw
            if amount is None:
                amount = 0.0
            code = (raw.get("currency_code") if isinstance(raw, dict) else code).upper()
            value_base = self._convert_to_base(code, float(amount), base.upper(), rates)
            total += value_base
            table.add_row([code, f"{amount:,.6f}", f"{value_base:,.2f}"])

        print(table)
        print("-" * 33)
        print(f"ИТОГО: {total:,.2f} {base.upper()}")

    def _cmd_buy(self, args: list[str]) -> None:
        """Покупка за USD."""
        code = self._get_flag(args, "--currency") or (args[0] if args else None)
        amount_raw = self._get_flag(args, "--amount")
        if not code or amount_raw is None:
            print("usage: buy --currency <CODE> --amount <QTY>")
            return
        try:
            qty = float(amount_raw)
            res = buy(self.current_user["user_id"], code.upper(), qty)
            print(
                f"Покупка выполнена: {qty:,.6f} {code.upper()} по курсу {res['rate']:,.4f} USD\n"
                f"Изменения в портфеле:\n"
                f"- {code.upper()}: было {res.get('before', 0):,.4f} → стало {res.get('after', 0):,.4f}\n"
                f"Оценочная стоимость покупки: {res['usd_spent']:,.2f} USD"
            )
        except ValueError:
            print("Ошибка: 'amount' должен быть числом")
        except (InvalidCurrencyError, ValidationError, InsufficientFundsError, CurrencyNotFoundError) as exc:
            print(f"Ошибка: {exc}")
        except StaleRatesError as exc:
            print(f"Ошибка: {exc}")
        except ApiRequestError:
            print(f"Ошибка: Не удалось получить курс для {code.upper()}→USD")
        except Exception as exc:
            self.logger.error(f"buy fail: {exc}")
            print(f"Ошибка: {exc}")

    def _cmd_sell(self, args: list[str]) -> None:
        """Продажа валюты."""
        code = self._get_flag(args, "--currency") or (args[0] if args else None)
        amount_raw = self._get_flag(args, "--amount")
        if not code or amount_raw is None:
            print("usage: sell --currency <CODE> --amount <QTY>")
            return
        try:
            qty = float(amount_raw)
            res = sell(self.current_user["user_id"], code.upper(), qty)
            print(
                f"Продажа выполнена: {qty:,.6f} {code.upper()} по курсу {res['rate']:,.4f} USD\n"
                f"Изменения в портфеле:\n"
                f"- {code.upper()}: было {res.get('before', 0):,.4f} → стало {res.get('after', 0):,.4f}\n"
                f"Оценочная выручка: {res['usd_received']:,.2f} USD"
            )
        except ValueError:
            print("Ошибка: 'amount' должен быть числом")
        except (InvalidCurrencyError, InsufficientFundsError, ValidationError, CurrencyNotFoundError) as exc:
            print(f"Ошибка: {exc}")
        except ApiRequestError:
            print(f"Ошибка: Не удалось получить курс для {code.upper()}→USD")
        except StaleRatesError as exc:
            print(f"Ошибка: {exc}")
        except Exception as exc:
            self.logger.error(f"sell fail: {exc}")
            print(f"Ошибка: {exc}")


def main() -> None:
    """Точка входа для poetry script."""
    TradingCLI().run()


if __name__ == "__main__":
    main()
