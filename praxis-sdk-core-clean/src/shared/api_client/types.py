from __future__ import annotations

from abc import abstractmethod
from types import TracebackType
from typing import Protocol


class Command[R, O](Protocol):
    __slots__ = ()

    @abstractmethod
    def execute(self, __resource: R) -> O:
        raise NotImplementedError


class Client[R](Protocol):
    __slots__ = ()

    @abstractmethod
    def __call__[O](self, __command: Command[R, O]) -> O:
        raise NotImplementedError

    @abstractmethod
    async def __aenter__(self) -> Client:
        raise NotImplementedError

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        raise NotImplementedError
