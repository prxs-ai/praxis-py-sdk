from typing import Any

from .base import Message


class Generic(Message):
    source: str
    content: str
    metadata: dict[str, Any] | None = None
