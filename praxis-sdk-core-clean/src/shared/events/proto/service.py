from google.protobuf.json_format import MessageToDict

from services.shared.events.models import Model
from services.shared.events.types import Service

from .map import get_message_type


class ProtoService(Service[Model, bytes]):
    def serialize[C: Model](self, model: C) -> bytes:
        return get_message_type(type(model))(**model.dump()).SerializeToString()

    def deserialize[C: Model](self, data: bytes, type_: type[C]) -> C:
        msg = get_message_type(type_)()
        msg.ParseFromString(data)

        return type_(
            **MessageToDict(
                msg,
                preserving_proto_field_name=True,
                use_integers_for_enums=True,
            )
        )
