from abc import abstractmethod
from typing import Protocol


class Service[I, O](Protocol):
    @abstractmethod
    def serialize(self, __message: I) -> O:
        raise NotImplementedError

    @abstractmethod
    def deserialize(self, __data: O, __type: type[I]) -> I:
        raise NotImplementedError
