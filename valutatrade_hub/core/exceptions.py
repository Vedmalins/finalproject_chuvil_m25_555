"""Пользовательские исключения для finalproject_chuvil_m25_555."""


class ValutatradeError(Exception):
    """Базовое исключение приложения."""


class InsufficientFundsError(ValutatradeError):
    """Недостаточно средств на счёте."""

    def __init__(self, available: float, required: float, code: str) -> None:
        self.available = available
        self.required = required
        self.code = code
        message = (
            f"Недостаточно средств: доступно {available} {code}, требуется {required} {code}"
        )
        super().__init__(message)


class CurrencyNotFoundError(ValutatradeError):
    """Запрошенная валюта не найдена."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"Неизвестная валюта '{code}'")


class ApiRequestError(ValutatradeError):
    """Ошибка обращения к внешнему API."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")


class AuthenticationError(ValutatradeError):
    """Ошибка аутентификации."""


class ValidationError(ValutatradeError):
    """Ошибка валидации входных данных."""


class UserNotFoundError(ValutatradeError):
    """Пользователь не найден."""

    def __init__(self, identifier: str | int) -> None:
        self.identifier = identifier
        super().__init__(f"Пользователь не найден: {identifier}")


class UserAlreadyExistsError(ValutatradeError):
    """Пользователь уже существует."""

    def __init__(self, username: str) -> None:
        self.username = username
        super().__init__(f"Пользователь '{username}' уже существует")


class InvalidCurrencyError(ValutatradeError):
    """Неверный код валюты."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"Неверный код валюты: {code}")


class RateFetchError(ValutatradeError):
    """Ошибка получения курса валюты."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Не удалось получить курс: {reason}")


# совместимость
ValutaTradeError = ValutatradeError
