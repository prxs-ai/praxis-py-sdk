from datetime import datetime

from google.protobuf.timestamp_pb2 import Timestamp

from services.shared.events.models import Model

from .map import fill_message, get_message_type


class ProtoService:
    def serialize[C: Model](self, model: C) -> bytes:
        return fill_message(
            get_message_type(type(model))(), model.dump()
        ).SerializeToString()

    def deserialize[C: Model](self, data: bytes, type_: type[C]) -> C:
        msg = get_message_type(type_)()
        msg.ParseFromString(data)

        fields = [field.name for field in msg.DESCRIPTOR.fields]

        data = {}
        for field in fields:
            val = getattr(msg, field, None)
            match val:
                case Timestamp():
                    if val.SetInParent():
                        val = val.ToDatetime()
                    else:
                        val = None
            data[field] = val

        return type_(**data)
