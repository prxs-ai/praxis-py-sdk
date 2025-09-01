from collections.abc import Iterable as _Iterable
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from services.shared.events.proto.schemas import meta_pb2 as _meta_pb2

DESCRIPTOR: _descriptor.FileDescriptor

class Source(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    OTHER: _ClassVar[Source]
    TELEGRAM: _ClassVar[Source]
    TWITTER: _ClassVar[Source]

OTHER: Source
TELEGRAM: Source
TWITTER: Source

class NewsMeta(_message.Message):
    __slots__ = ("replies", "views", "reactions", "created_at")
    REPLIES_FIELD_NUMBER: _ClassVar[int]
    VIEWS_FIELD_NUMBER: _ClassVar[int]
    REACTIONS_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    replies: int
    views: int
    reactions: int
    created_at: _timestamp_pb2.Timestamp
    def __init__(
        self,
        replies: int | None = ...,
        views: int | None = ...,
        reactions: int | None = ...,
        created_at: _timestamp_pb2.Timestamp | _Mapping | None = ...,
    ) -> None: ...

class News(_message.Message):
    __slots__ = ("event_meta", "source", "content", "meta", "tags", "author")
    EVENT_META_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    META_FIELD_NUMBER: _ClassVar[int]
    TAGS_FIELD_NUMBER: _ClassVar[int]
    AUTHOR_FIELD_NUMBER: _ClassVar[int]
    event_meta: _meta_pb2.EventMeta
    source: Source
    content: str
    meta: NewsMeta
    tags: _containers.RepeatedScalarFieldContainer[str]
    author: str
    def __init__(
        self,
        event_meta: _meta_pb2.EventMeta | _Mapping | None = ...,
        source: Source | str | None = ...,
        content: str | None = ...,
        meta: NewsMeta | _Mapping | None = ...,
        tags: _Iterable[str] | None = ...,
        author: str | None = ...,
    ) -> None: ...
