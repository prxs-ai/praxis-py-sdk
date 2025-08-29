from dataclasses import dataclass
from typing import Generic, TypeVar

from google.protobuf.json_format import MessageToDict
from services.shared.events.models import Model
from services.shared.events.types import Service

from .map import get_message_type

M = TypeVar("M", bound=Model)


@dataclass(slots=True)
class ProtoService(Service[M, bytes], Generic[M]):
    _model_type: type[M]

    def serialize(self, model: M) -> bytes:
        return get_message_type(type(model))(**model.dump()).SerializeToString()

    def deserialize(self, data: bytes) -> M:
        msg = get_message_type(self._model_type)()
        msg.ParseFromString(data)

        return self._model_type(
            **MessageToDict(
                msg,
                preserving_proto_field_name=True,
                use_integers_for_enums=True,
            )
        )
