from typing import Generic, TypeVar

from base_provider.abc import AbstractDataSink, DataMode
from base_provider.sinks.config import KafkaDataSinkConfig, get_kafka_data_sink_config
from fast_depends import Depends, inject
from faststream.kafka import KafkaBroker

T = TypeVar("T")


class KafkaDataSink(AbstractDataSink[T], Generic[T]):
    """Kafka implementation of data sink."""

    def __init__(self, config: KafkaDataSinkConfig, broker: KafkaBroker):
        self.config = config
        self.broker = broker

        self.is_connected = False

    @property
    def mode(self) -> DataMode:
        return DataMode.ASYNC

    async def connect(self):
        """Establish connection to Kafka."""
        await self.broker.start()
        self.is_connected = True

    async def write(self, data: T, *args, topic: str, **kwargs) -> T:
        if not self.is_connected:
            await self.connect()

        await self.broker.publish(data, topic=topic)

        return data


@inject
def get_kafka_broker(config: KafkaDataSinkConfig = Depends(get_kafka_data_sink_config)) -> KafkaBroker:
    return KafkaBroker(config.kafka_bootstrap_uri)


@inject
def get_kafka_data_sink(
    config: KafkaDataSinkConfig = Depends(get_kafka_data_sink_config),
    broker: KafkaBroker = Depends(get_kafka_broker),
) -> KafkaDataSink:
    return KafkaDataSink(config, broker)
