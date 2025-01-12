from abc import abstractmethod
from typing import Awaitable

from services.shared.api_client.types import Command

from .session import Session


class AbstractCommand[R](Command[Session, Awaitable[R]]):
    __slots__ = ()

    async def execute(self, session: Session) -> R:
        return await self._execute(session)

    @abstractmethod
    async def _execute(self, session: Session) -> R:
        raise NotImplementedError
