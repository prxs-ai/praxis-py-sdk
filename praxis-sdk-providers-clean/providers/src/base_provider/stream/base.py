from typing import Any, Generic, TypeVar

from base_provider.abc import AbstractDataProcessor, AbstractDataSink, AbstractDataSource, AbstractDataStream
from base_provider.stream.config import BaseDataStreamConfig

T = TypeVar("T")
U = TypeVar("U")


class BaseDataStream(AbstractDataStream[T, U]):
    """Base implementation of data Stream."""

    def __init__(self, config: BaseDataStreamConfig):
        self.config = config

    def setup(self, source: AbstractDataSource[T], processors: list[AbstractDataProcessor[Any, Any]], sinks: list[AbstractDataSink[U]]) -> None:
        self.source = source
        self.processors = processors
        self.sinks = sinks

        self._is_running = False

    async def start(self) -> None:
        """Start all data streams."""
        self._is_running = True

    async def process_item(self, item: Any):
        """Process a single item."""
        result = item
        for processor in self.processors:
            result = await processor.process(result)
        return result

    async def process_batch(self, batch: list[Any]) -> list[Any]:
        """Process a batch of items."""
        results = []
        for item in batch:
            results.append(await self.process_item(item))
        return results

    async def run_once(self, *args, **kwargs) -> U:
        """Run the data pipeline."""
        data_list = await self.source.fetch(*args, **kwargs)
        data_list = await self.process_batch(data_list)
        # do not lanch the sink, just return the data
        return data_list

def get_data_stream(config: BaseDataStreamConfig) -> BaseDataStream:
    return BaseDataStream(config)
