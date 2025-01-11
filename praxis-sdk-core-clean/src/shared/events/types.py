from abc import abstractmethod
from typing import Protocol


class Service[I, O](Protocol):
    __slots__ = ()

    @abstractmethod
    def serialize(self, __message: I) -> O:
        raise NotImplementedError

    @abstractmethod
    def deserialize(self, __data: O) -> I:
        raise NotImplementedError
