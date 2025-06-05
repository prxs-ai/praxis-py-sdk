from __future__ import annotations

from abc import abstractmethod
from types import TracebackType
from typing import Protocol, TypeVar, Generic

R = TypeVar("R")


class API(Protocol, Generic[R]):
    __slots__ = ()

    @abstractmethod
    async def __aenter__(self) -> API[R]:
        raise NotImplementedError

    @abstractmethod
    async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc_val: BaseException | None,
            exc_tb: TracebackType | None,
    ) -> None:
        raise NotImplementedError
