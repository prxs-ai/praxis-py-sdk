from datetime import datetime
from enum import IntEnum
from typing import Any

from services.shared.events.proto import NewsMeta as _NewsMeta
from services.shared.events.proto import News as _News
from .meta import EventMeta
from .base import Model
from .utils import register


class Source(IntEnum):
    OTHER = 0
    TELEGRAM = 1
    TWITTER = 2


@register(_NewsMeta)
class NewsMeta(Model):
    replies: int
    views: int
    reactions: int

    created_at: datetime | None  


@register(_News)
class News(Model):
    event_meta: EventMeta | None
    news_meta: NewsMeta
    content: dict[str, Any]
    source: Source = Source.OTHER
