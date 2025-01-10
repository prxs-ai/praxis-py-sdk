__all__ = (
    "EventMeta",
    "News",
    "Source",
    "NewsMeta",
)

from .gen.meta_pb2 import EventMeta
from .gen.news_pb2 import News, NewsMeta, Source
