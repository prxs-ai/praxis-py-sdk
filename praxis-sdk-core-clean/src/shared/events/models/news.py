from enum import IntEnum
from typing import ClassVar
from  pydantic import Field
from .base import Model
from .meta import EventMeta
from .timedelta import Timedelta
from .topic import Topic


class Source(IntEnum):
    OTHER = 0
    TELEGRAM = 1
    TWITTER = 2


class NewsMeta(Model):
    replies: int | None = None
    views: int | None = None
    reactions: int | None = None

    created_at: Timedelta | None = None


class News(Model):
    __topics__: ClassVar[tuple[Topic, ...]] = (Topic.NEWS,)

    content: str
    meta: NewsMeta
    event_meta: EventMeta
    tags: list[str] = Field(default_factory=list)
    source: Source = Source.OTHER

    @property
    def source_as_string(self) -> str:
        return self.source.name
