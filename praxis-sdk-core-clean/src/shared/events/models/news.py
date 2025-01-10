from datetime import datetime
from enum import IntEnum
from typing import Any, ClassVar

from .base import Model
from .meta import EventMeta
from .topic import Topic


class Source(IntEnum):
    OTHER = 0
    TELEGRAM = 1
    TWITTER = 2


class NewsMeta(Model):
    replies: int | None = None
    views: int | None = None
    reactions: int | None = None

    created_at: datetime | None = None


class News(Model):
    __topics__: ClassVar[tuple[Topic, ...]] = (Topic.NEWS,)

    news_meta: NewsMeta
    content: dict[str, Any]
    source: Source = Source.OTHER
    event_meta: EventMeta | None = None
