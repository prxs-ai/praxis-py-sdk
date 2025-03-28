from typing import Generic, TypeVar

from base_provider.abc import AbstractDataSink, DataMode
from base_provider.sink.config import KafkaDataSinkConfig, get_kafka_data_sink_config
from fast_depends import Depends, inject
from faststream.kafka import KafkaBroker

T = TypeVar("T")


class KafkaDataSink(AbstractDataSink[T], Generic[T]):
    """Kafka implementation of data sink."""

    def __init__(self, config: KafkaDataSinkConfig, broker: KafkaBroker):
        self.config = config
        self.broker = broker

    @property
    def mode(self) -> DataMode:
        return DataMode.ASYNC

    async def write(self, data: T, topic: str) -> T:
        await self.broker.publish(data, topic=topic)

        return data


@inject
def get_kafka_broker(config: KafkaDataSinkConfig = Depends(get_kafka_data_sink_config)) -> KafkaBroker:
    return KafkaBroker(bootstrap_servers=config.kafka_bootstrap_uri)


@inject
def get_kafka_data_sink(config: KafkaDataSinkConfig, broker: KafkaBroker = Depends(get_kafka_broker)) -> KafkaDataSink:
    return KafkaDataSink(config, broker)
