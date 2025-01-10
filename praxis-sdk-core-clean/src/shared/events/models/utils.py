from typing import Any, Callable

from services.shared.events.proto import Proto

ModelRegistry: dict[type[Any], type[Proto]] = {}


def register[C](proto: Proto) -> Callable[[type[C]], type[C]]:
    def wrapper(cls: type[C]) -> type[C]:
        ModelRegistry[cls] = proto
        return cls

    return wrapper
