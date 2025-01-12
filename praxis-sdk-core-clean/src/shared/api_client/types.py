from abc import abstractmethod
from typing import Protocol


class Command[R, O](Protocol):
    @abstractmethod
    def execute(self, __resource: R) -> O:
        raise NotImplementedError


class Client[R](Protocol):
    @abstractmethod
    def __call__[O](self, __command: Command[R, O]) -> O:
        raise NotImplementedError
