from abc import abstractmethod
from typing import Protocol


class Service[I, O](Protocol):
    @abstractmethod
    def serialize(self, __data: I) -> O:
        raise NotImplementedError

    @abstractmethod
    def deserialize(self, __data: O) -> I:
        raise NotImplementedError
