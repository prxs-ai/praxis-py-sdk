from abc import abstractmethod
from typing import Generic, Protocol, TypeVar

I = TypeVar("I")
O = TypeVar("O")


class Service(Protocol, Generic[I, O]):
    __slots__ = ()

    @abstractmethod
    def serialize(self, __message: I) -> O:
        raise NotImplementedError

    @abstractmethod
    def deserialize(self, __data: O) -> I:
        raise NotImplementedError
