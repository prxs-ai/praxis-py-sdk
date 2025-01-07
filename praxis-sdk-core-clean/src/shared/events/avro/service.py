from confluent_kafka.schema_registry.schema_registry_client import (  # type: ignore
    SchemaRegistryClient,
)
from confluent_kafka.serializing_producer import SerializationContext  # type: ignore

from services.shared.events.messages import Message
from services.shared.events.types import Service

from .mapper import get_deserializer, get_serializer


class AvroService[I: Message](Service[I, bytes]):
    __slots__ = (
        "_client",
        "_serializer",
        "_deserializer",
    )

    def __init__(self, client: SchemaRegistryClient, message_type: type[I]) -> None:
        self._client = client
        self._serializer = get_serializer(client, message_type)
        self._deserializer = get_deserializer(client, message_type)

    def serialize(self, msg: I) -> bytes:
        return self._serializer(
            msg.to_dict(include_topic=True),
            SerializationContext(msg.__topic__, "value"),
        )

    def deserialize(self, data: bytes) -> I:
        return self._deserializer(data)
