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

# class Proto(Protocol):
#     @abstractmethod
#     def IsInitialized(self) -> bool:
#         raise NotImplementedError

#     @abstractmethod
#     def __str__(self) -> str:
#         raise NotImplementedError

#     @abstractmethod
#     def CopyFrom(self, other_msg: Proto) -> None:
#         raise NotImplementedError

#     @abstractmethod
#     def Clear(self) -> None:
#         raise NotImplementedError

#     @abstractmethod
#     def SerializeToString(self) -> bytes:
#         raise NotImplementedError

#     @abstractmethod
#     def ParseFromString(data, __data: bytes) -> Proto:
#         raise NotImplementedError
