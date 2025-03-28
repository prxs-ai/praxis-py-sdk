import asyncio
from typing import Any, TypeVar

from base_provider.abc import AbstractDataProcessor, AbstractDataSink, AbstractDataSource, AbstractDataStream, DataMode
from base_provider.stream.config import BaseDataStreamConfig

T = TypeVar("T")
U = TypeVar("U")


class BaseDataStream(AbstractDataStream[T, U]):
    """Base implementation of data Stream."""

    def __init__(self, config: BaseDataStreamConfig):
        self.config = config

    def setup(
        self,
        source: AbstractDataSource[T],
        processors: list[AbstractDataProcessor[Any, Any]],
        sinks: list[AbstractDataSink[U]],
    ) -> None:
        self.source = source
        self.processors = processors
        self.sinks = sinks

        self._is_running = False

    @property
    def models(self) -> dict[str, Any]:
        """Return the models supported by the stream."""
        return {}

    @property
    def service_levels(self) -> dict[str, Any]:
        """Return the service levels supported by the stream."""
        return {"availability": {"uptime": "99.9%"}, "retention": {"duration": "30 days"}}

    @property
    def servers(self) -> dict[str, Any]:
        """Return the servers supported by the stream."""
        return {}

    @property
    def supported_modes(self) -> set[DataMode]:
        """Return the supported modes."""
        return DataMode.all()

    async def start(self) -> None:
        """Start all data streams."""
        self._is_running = True

    async def process_item(self, item: Any, filters: dict[str, Any]):
        """Process a single item."""
        result = item
        for processor in self.processors:
            result = await processor.process(result, filters)
        return result

    async def process_batch(self, batch: list[Any], filters: dict[str, Any]) -> list[Any]:
        """Process a batch of items."""
        results = []
        for item in batch:
            results.append(await self.process_item(item, filters))
        return results

    async def run_once(self, *args, filters: dict[str, Any], **kwargs) -> U:
        """Run the data pipeline."""
        data_list = await self.source.fetch(*args, **kwargs)
        data_list = await self.process_batch(data_list, filters=filters)
        # do not lanch the sink, just return the data
        return data_list

    async def run(self, *args, filters: dict[str, Any], **kwargs) -> None:
        """Run the data pipeline."""
        data_list = await self.source.fetch(*args, **kwargs)
        data_list = await self.process_batch(data_list, filters=filters)

        await asyncio.gather(*[sink.write(data_list, *args, **kwargs) for sink in self.sinks])

    async def stop(self) -> None:
        """Stop all data streams."""
        self._is_running = False


def get_data_stream(config: BaseDataStreamConfig) -> BaseDataStream:
    return BaseDataStream(config)
