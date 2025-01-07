from confluent_kafka.schema_registry.schema_registry_client import (  # type: ignore
    SchemaRegistryClient,
)

from services.shared.events.messages import Message
from services.shared.events.types import Service

from .mapper import get_deserializer, get_serializer


class AvroService[I: Message](Service[I, bytes]):
    __slots__ = (
        "_client",
        "_serializer",
        "_deserializer",
    )

    def __init__(self, client: SchemaRegistryClient, message: type[I]) -> None:
        self._client = client
        self._serializer = get_serializer(client)
        self._deserializer = get_deserializer(client)

    def serialize(self, msg: I) -> bytes:
        return self._serializer(msg.to_dict())

    def deserialize(self, data: bytes) -> I:
        return self._deserializer(data)
