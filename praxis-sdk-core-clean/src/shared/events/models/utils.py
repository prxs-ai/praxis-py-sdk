from typing import Callable

from services.shared.events.proto import Proto

from .topic import Topic


def register[C](proto: Proto, *topics: Topic) -> Callable[[type[C]], type[C]]:
    def wrapper(cls: type[C]) -> type[C]:
        cls.__proto__ = proto
        cls.__topics__ = topics
        return cls

    return wrapper
