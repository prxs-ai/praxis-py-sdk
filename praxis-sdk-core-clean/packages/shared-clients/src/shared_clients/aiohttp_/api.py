from types import TracebackType
from typing import Generic, Self, TypeVar

from shared_clients.aiohttp_.session import AiohttpSession
from shared_clients.types import API

S = TypeVar("S", bound=AiohttpSession)


class AiohttpAPI(API[S], Generic[S]):
    __slots__ = ("_session",)

    def __init__(self, session: S) -> None:
        self._session = session

    async def __aenter__(self) -> Self:
        await self._session.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        return await self._session.__aexit__(exc_type, exc_val, exc_tb)
