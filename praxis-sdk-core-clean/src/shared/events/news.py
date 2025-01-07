from typing import Any

from .base import Event


class News(Event):
    source: str
    content: dict[str, Any]
    metadata: dict[str, Any]
