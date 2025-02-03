__all__ = (
    "AbstractCommand",
    "TweetScoutSession",
    "Request",
    "Response",
)

from typing import Any

from pydantic import BaseModel

from services.shared.api_client.aiohttp_ import AbstractCommand as _AbstractCommand
from services.shared.api_client.tweetscout.session import TweetScoutSession


class Request(BaseModel):
    def dump(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)


class Response(BaseModel): ...


class AbstractCommand[I: Request, R: Response](_AbstractCommand[TweetScoutSession, R]):
    __slots__ = "data"

    def __init__(self, data: I) -> None:
        self.data = data
