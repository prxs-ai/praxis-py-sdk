__all__ = (
    "EventMeta",
    "News",
    "Source",
    "NewsMeta",
    "Proto",
)

from typing import Protocol

from .meta_pb2 import EventMeta
from .news_pb2 import News, NewsMeta, Source


class Proto(Protocol): ...
