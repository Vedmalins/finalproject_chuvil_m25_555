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
            "rate": self._cmd_rate,
            "update": self._cmd_update,
        }
        self.auth_cmds = {
            "portfolio": self._cmd_portfolio,
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

    # --- команды общие ---

    def _cmd_help(self, args: list[str]) -> None:
        """Печатает список команд."""
        print("\nОбщие команды:")
        print("  help          показать подсказку")
        print("  exit|quit     выход")
        print("  register      регистрация")
        print("  login         вход")
        print("  rates         все курсы")
        print("  rate <код>    курс одной валюты")
        print("  update        обновить курсы\n")
        if self.current_user:
            print("Команды после входа:")
            print("  portfolio     показать кошельки")
            print("  buy <код> <USD>   купить за USD")
            print("  sell <код> <amt>  продать валюту")
            print("  logout        выйти из аккаунта\n")

    def _cmd_exit(self, args: list[str] | None = None) -> None:
        """Завершает цикл."""
        print("До встречи")
        self.running = False

    def _cmd_register(self, args: list[str]) -> None:
        """Регистрация нового пользователя."""
        try:
            username = input("Имя: ").strip()
            password = getpass.getpass("Пароль: ")
            confirm = getpass.getpass("Повтор: ")
            if password != confirm:
                print("Пароли разные")
                return
            result = register(username, password)
            print(f"Готово, ваш id: {result['user_id']}")
        except UserAlreadyExistsError as exc:
            print(f"Ошибка: {exc}")
        except ValidationError as exc:
            print(f"Ошибка: {exc}")

    def _cmd_login(self, args: list[str]) -> None:
        """Вход в систему."""
        if self.current_user:
            print("Уже вошли, сначала logout")
            return
        try:
            username = input("Имя: ").strip()
            password = getpass.getpass("Пароль: ")
            data = login(username, password)
            self.current_user = {"user_id": data["user_id"], "username": data["username"]}
            print(f"Привет, {username}")
        except (AuthenticationError, UserNotFoundError) as exc:
            print(f"Ошибка: {exc}")

    def _cmd_rates(self, args: list[str]) -> None:
        """Показывает таблицу курсов."""
        rates = get_all_rates()
        if not rates:
            print("Курсы пустые, попробуйте update")
            return
        table = PrettyTable()
        table.field_names = ["Валюта", "Курс к USD"]
        table.align["Валюта"] = "l"
        table.align["Курс к USD"] = "r"
        for code, rate in sorted(rates.items()):
            table.add_row([code, f"{rate:,.4f}"])
        print(table)

    def _cmd_rate(self, args: list[str]) -> None:
        """Курс конкретной валюты."""
        if not args:
            print("usage: rate <код>")
            return
        try:
            res = get_rate(args[0].upper())
            print(f"{args[0].upper()} = {res['rate']:,.4f} USD")
        except InvalidCurrencyError as exc:
            print(f"Ошибка: {exc}")
        except StaleRatesError as exc:
            print(f"Ошибка: {exc}")

    def _cmd_update(self, args: list[str]) -> None:
        """Тянет свежие курсы из сетки."""
        print("Обновляю курсы, секундочку...")
        try:
            run_once()
            print("Готово")
        except Exception as exc:
            self.logger.error(f"update fail: {exc}")
            print(f"Ошибка: {exc}")

    # --- команды после логина ---

    def _cmd_logout(self, args: list[str]) -> None:
        """Выход из аккаунта."""
        self.current_user = None
        print("Вышли из аккаунта")

    def _cmd_portfolio(self, args: list[str]) -> None:
        """Показывает баланс по валютам."""
        result = show_portfolio(self.current_user["user_id"])
        wallets = result.get("portfolio", {}).get("wallets", {})
        if not wallets:
            print("Портфель пуст, купите что-нибудь")
            return
        table = PrettyTable()
        table.field_names = ["Валюта", "Количество"]
        table.align["Валюта"] = "l"
        table.align["Количество"] = "r"
        for code, amount in wallets.items():
            table.add_row([code, f"{amount:,.6f}"])
        print(table)

    def _cmd_buy(self, args: list[str]) -> None:
        """Покупка за USD."""
        if len(args) < 2:
            print("usage: buy <код> <usd>")
            return
        try:
            usd_amount = float(args[1])
            res = buy(self.current_user["user_id"], args[0].upper(), usd_amount)
            print(f"Куплено {res['amount']:,.6f} {args[0].upper()} по {res['rate']:,.4f}")
        except (InvalidCurrencyError, ValidationError) as exc:
            print(f"Ошибка: {exc}")
        except StaleRatesError as exc:
            print(f"Ошибка: {exc}")
        except Exception as exc:
            self.logger.error(f"buy fail: {exc}")
            print(f"Ошибка: {exc}")

    def _cmd_sell(self, args: list[str]) -> None:
        """Продажа валюты."""
        if len(args) < 2:
            print("usage: sell <код> <qty>")
            return
        try:
            qty = float(args[1])
            res = sell(self.current_user["user_id"], args[0].upper(), qty)
            print(f"Продано {qty:,.6f} {args[0].upper()} за {res['usd_received']:,.2f} USD")
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
