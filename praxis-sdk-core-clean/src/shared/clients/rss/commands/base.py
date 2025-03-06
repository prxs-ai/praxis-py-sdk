__all__ = (
    "AbstractCommand",
    "AiohttpSession",
    "Request",
    "Response",
)

from typing import Any

from pydantic import BaseModel

from services.shared.clients.aiohttp_ import AbstractCommand as _AbstractCommand
from services.shared.clients.aiohttp_ import AiohttpSession


class Request(BaseModel):
    def dump(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)


class Response(BaseModel): ...


class AbstractCommand[I: Request, R: Response](_AbstractCommand[AiohttpSession, R]):
    __slots__ = "data"

    def __init__(self, data: I) -> None:
        self.data = data
