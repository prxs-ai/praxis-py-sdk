__all__ = (
    "EventMeta",
    "News",
    "Source",
    "NewsMeta",
    "Message",
)

from google.protobuf.message import Message

from .meta_pb2 import EventMeta
from .news_pb2 import News, NewsMeta, Source
