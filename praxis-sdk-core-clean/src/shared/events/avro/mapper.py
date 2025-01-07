from typing import Final

from confluent_kafka.schema_registry.avro import (  # type: ignore
    AvroDeserializer,
    AvroSerializer,
)
from confluent_kafka.schema_registry.schema_registry_client import (  # type: ignore
    SchemaRegistryClient,
)

from services.shared.events.messages import Message, NewsMessage

news_schema = """
{
  "type": "record",
  "name": "Post",
  "fields": [
    {
      "name": "name",
      "type": "string"
    },
    {
      "name": "source",
      "type": "string"
    },
    {
      "name": "content",
      "type": {
        "type": "map",
        "values": "string"
      }
    },
    {
      "name": "id",
      "type": "string"
    },
    {
      "name": "metadata",
      "type": {
        "type": "map",
        "values": "string"
      }
    }
  ]
}
"""


_SchemaMapper: Final[dict[type[Message], str]] = {NewsMessage: news_schema}


def get_serializer(
    client: SchemaRegistryClient,
    msg: type[Message],
) -> AvroSerializer:
    return AvroSerializer(client, _SchemaMapper[msg], msg.to_dict)


def get_deserializer(
    client: SchemaRegistryClient,
    msg: type[Message],
) -> AvroDeserializer:
    return AvroDeserializer(client, _SchemaMapper[msg], msg.from_dict)
