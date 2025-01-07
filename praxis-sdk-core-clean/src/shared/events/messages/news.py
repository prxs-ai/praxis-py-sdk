from typing import Any, ClassVar

from .base import Message


class NewsMessage(Message):
    __topic__: ClassVar[str] = "news"
    id: str
    name: str
    source: str
    content: dict[str, Any]
    metadata: dict[str, Any] | None = None
