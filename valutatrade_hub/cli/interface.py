"""Простой CLI для работы с кошельком, без лишних украшений."""

from __future__ import annotations

import getpass
import shlex
from typing import Any

from prettytable import PrettyTable

from valutatrade_hub.core.exceptions import (
    AuthenticationError,
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

            "rates": self._cmd_rates,
            "show-rates": self._cmd_rates,

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

    # --- утилиты ввода/вывода ---

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
        print("  rates|show-rates          все курсы")
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
            print(
                f"Курс {from_code.upper()}→{to_code.upper()}: {res['rate']:,.6f} "
                f"(обновлено: {res.get('updated_at', 'n/a')})"
            )
        except (InvalidCurrencyError, StaleRatesError, ValidationError) as exc:
            print(f"Ошибка: {exc}")


    def _cmd_update(self, args: list[str]) -> None:
        """Тянет свежие курсы из сетки."""
        print("Обновляю курсы, секундочку...")

        try:
            result = run_once()  # теперь возвращает словарь
        except Exception as exc:
            # если действительно фатальная,
            # её можно показать пользователю.
            self.logger.error(f"update fail: {exc}")
            print(f"Ошибка обновления: {exc}")
            return

        # Нефатальные предупреждения
        warnings = []
        if isinstance(result, dict):
            warnings = result.get("warnings", []) or []

        for w in warnings:
            print(f"NOTE: {w}")

        print("Готово")


    # команды после логина

    def _cmd_logout(self, args: list[str]) -> None:
        """Выход из аккаунта."""
        self.current_user = None
        print("Вышли из аккаунта")

    def _cmd_portfolio(self, args: list[str]) -> None:
        """Показывает баланс по валютам."""
        base = self._get_flag(args, "--base") or "USD"
        result = show_portfolio(self.current_user["user_id"], base)
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
        for code, amount in wallets.items():
            value_base = self._convert_to_base(code, amount, base.upper(), rates)
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
                f"Оценочная стоимость: {res['usd_spent']:,.2f} USD"
            )
        except (InvalidCurrencyError, ValidationError, InsufficientFundsError) as exc:
            print(f"Ошибка: {exc}")
        except StaleRatesError as exc:
            print(f"Ошибка: {exc}")
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
                f"Выручка: {res['usd_received']:,.2f} USD"
            )
        except (InvalidCurrencyError, InsufficientFundsError, ValidationError) as exc:
            print(f"Ошибка: {exc}")
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
