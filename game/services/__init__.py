"""
Бизнес-логика игры. Views только разбирают запрос и отдают ответ,
всё остальное — здесь.

Ошибки игровых правил выбрасываются как GameError и превращаются
во views в ответ {"detail": ...} с нужным HTTP-статусом.
"""


class GameError(Exception):
    """Нарушение игрового правила (недостаточно монет, место занято и т.п.)."""

    def __init__(self, detail: str, status: int = 400, **extra):
        super().__init__(detail)
        self.detail = detail
        self.status = status
        self.extra = extra

    def as_response_data(self) -> dict:
        return {"detail": self.detail, **self.extra}
