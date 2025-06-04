from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import timestamp_pb2 as _timestamp_pb2

DESCRIPTOR: _descriptor.FileDescriptor

class EventMeta(_message.Message):
    __slots__ = ("id", "created_at")
    ID_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    id: str
    created_at: _timestamp_pb2.Timestamp
    def __init__(
        self,
        id: str | None = ...,
        created_at: _timestamp_pb2.Timestamp | _Mapping | None = ...,
    ) -> None: ...
