import asyncio
from typing import Any, TypeVar

from base_provider.abc import (
    AbstractDataProcessor,
    AbstractDataSink,
    AbstractDataSource,
    AbstractDataStream,
    AbstractDataTrigger,
    DataMode,
)
from base_provider.sinks.const import DefaultSinkEntrypointType
from base_provider.stream.config import BaseDataStreamConfig, get_data_stream_config
from fast_depends import Depends, inject

T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")


class BaseDataStream(AbstractDataStream[T, U]):
    """Base implementation of data Stream."""

    def __init__(self, config: BaseDataStreamConfig):
        self.config = config

    def setup(
        self,
        triggers: dict[str, AbstractDataTrigger[E]],
        sources: dict[str, AbstractDataSource[T]],
        processors: dict[str, AbstractDataProcessor[Any, Any]],
        sinks: dict[str, AbstractDataSink[U]],
    ) -> None:
        self.triggers = triggers
        self.sources = sources
        self.processors = processors
        self.sinks = sinks

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

    async def process_item(self, item: Any, filters: dict[str, Any]):
        """Process a single item."""
        result = item
        for processor_name, processor in self.processors.items():
            result = await processor.process(result, **filters.pop(processor_name, {}))
        return result

    async def process_batch(self, batch: dict[str, list[Any]], filters: dict[str, Any]) -> list[Any]:
        """Process a batch of items."""
        results = {}
        for source, minibatch in batch.items():
            results[source] = await asyncio.gather(
                *[self.process_item(item, filters) for item in minibatch]
            )
        return results

    async def fetch_batch(self, *args, **kwargs) -> dict[str, list[T]]:
        """Fetch data from the source."""
        items = {}
        for source_name, source in self.sources.items():
            items[source_name] = await source.fetch(*args, **kwargs)
        return items

    async def write_item(self, item: Any, *args, **kwargs):
        """Write a single item."""
        results = {}
        for sink_name, sink in self.sinks.items():
            results[sink_name] = await sink.write(item, **kwargs.pop(sink_name, {}))
        return results

    async def write_batch(self, batch: dict[str, list[U]], *args, **kwargs) -> None:
        """Write data to sinks."""
        results = {}
        for source, minibatch in batch.items():
            results[source] = await asyncio.gather(
                *[self.write_item(item, *args, **kwargs) for item in minibatch]
            )
        return results


@inject
def get_data_stream(config: BaseDataStreamConfig = Depends(get_data_stream_config)) -> BaseDataStream:
    return BaseDataStream(config)
