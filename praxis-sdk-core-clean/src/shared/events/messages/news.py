from typing import Any, ClassVar

from .base import Message
from .topics import Topics


class NewsMessage(Message):
    __topic__: ClassVar[str] = Topics.NEWS
    id: str
    name: str
    source: str
    content: dict[str, Any]
    metadata: dict[str, Any] | None = None
