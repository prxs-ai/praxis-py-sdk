from abc import abstractmethod
from typing import Awaitable

from services.shared.api_client.types import Command

from .session import AiohttpSession


class AbstractCommand[S: AiohttpSession, R](Command[S, Awaitable[R]]):
    __slots__ = ()

    async def execute(self, session: S) -> R:
        return await self._execute(session)

    @abstractmethod
    async def _execute(self, session: S) -> R:
        raise NotImplementedError
