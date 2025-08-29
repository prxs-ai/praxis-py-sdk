from typing import Any


class APIError(BaseException):
    def __init__(self, status: int, message: str, **kwargs: Any) -> None:
        self.status = status
        self.message = message
        self.kwargs = kwargs

    def __repr__(self) -> str:
        return (
            f"\tStatus Code: {self.status}\n\tMessage: {self.message}\n\n{self.kwargs}"
        )
