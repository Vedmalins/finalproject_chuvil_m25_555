"""Ошибки проекта, собрал их в одном месте, чтобы самому не путаться."""


class ValutatradeError(Exception):
    """Базовая ошибка, от неё всё остальное наследую."""


class InsufficientFundsError(ValutatradeError):
    """Не хватает денег на балансе, обидно."""

    def __init__(self, available: float, required: float, code: str) -> None:
        self.available = available
        self.required = required
        self.code = code
        message = (
            f"Недостаточно средств: доступно {available} {code}, требуется {required} {code}"
        )
        super().__init__(message)


class CurrencyNotFoundError(ValutatradeError):
    """Запросили валюту, которой у нас нет."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"Неизвестная валюта '{code}'")


class ApiRequestError(ValutatradeError):
    """Что-то пошло не так при обращении к внешнему API."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")


class AuthenticationError(ValutatradeError):
    """Неверный пароль или ещё какая-то auth беда."""


class ValidationError(ValutatradeError):
    """Данные кривые, надо поправить прежде чем работать."""


class UserNotFoundError(ValutatradeError):
    """Не нашли пользователя по ид/нику."""

    def __init__(self, identifier: str | int) -> None:
        self.identifier = identifier
        super().__init__(f"Пользователь не найден: {identifier}")


class UserAlreadyExistsError(ValutatradeError):
    """Пользователь с таким именем уже есть, сорян."""

    def __init__(self, username: str) -> None:
        self.username = username
        super().__init__(f"Пользователь '{username}' уже существует")


class InvalidCurrencyError(ValutatradeError):
    """Код валюты не похож на настоящий."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"Неверный код валюты: {code}")


class RateFetchError(ValutatradeError):
    """Не получилось стянуть курс валюты."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Не удалось получить курс: {reason}")


# алиас для совместимости
ValutaTradeError = ValutatradeError
