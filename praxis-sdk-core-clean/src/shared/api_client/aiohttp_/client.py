from types import TracebackType
from typing import Self

from services.shared.api_client.types import Client, Command

from .session import AiohttpSession


class AiohttpClient[S: AiohttpSession](Client[S]):
    __slots__ = ("_session",)

    def __init__(self, session: S) -> None:
        self._session = session

    def __call__[O](self, command: Command[S, O]) -> O:
        return command.execute(self._session)

    async def __aenter__(self) -> Self:
        return await self._session.__aenter__()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        return await self._session.__aexit__(exc_type, exc_val, exc_tb)
