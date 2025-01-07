import json

from services.shared.events.messages import Message
from services.shared.events.types import Service


class BasicService[I: Message](Service[I, bytes]):
    __slots__ = ("_msg_type",)

    def __init__(self, msg_init: type[I]) -> None:
        self._msg_type = msg_init

    def serialize(self, msg: I) -> bytes:
        return json.dumps(msg.model_dump())

    def deserialize(self, data: bytes) -> I:
        return self._msg_type(json.loads(data))
