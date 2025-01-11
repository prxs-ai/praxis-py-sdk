from google.protobuf.json_format import ParseDict
from google.protobuf.timestamp_pb2 import Timestamp

from services.shared.events.models import Model
from services.shared.events.types import Service

from .map import get_message_type


class ProtoService(Service[Model, bytes]):
    def serialize[C: Model](self, model: C) -> bytes:
        data = model.dump()
        del data["content"]
        message = ParseDict(
            data, get_message_type(type(model))(), ignore_unknown_fields=True
        )
        message.content.ad
        return message

    def deserialize[C: Model](self, data: bytes, type_: type[C]) -> C:
        msg = get_message_type(type_)()
        msg.ParseFromString(data)

        data = {}
        for desc, val in msg.ListFields():
            match val:
                case Timestamp():
                    if val.SetInParent():
                        val = val.ToDatetime()
                    else:
                        val = None
            data[desc.name] = val

        return type_(**data)
