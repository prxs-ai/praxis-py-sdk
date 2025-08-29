from typing import Generic, TypeVar

from base_provider.abc import AbstractDataSink, DataMode
from base_provider.sinks.config import BaseDataSinkConfig, get_data_sink_config
from fast_depends import Depends, inject

T = TypeVar("T")


class BaseDataSink(AbstractDataSink[T], Generic[T]):
    """Base implementation of data sink."""

    def __init__(self, config: BaseDataSinkConfig):
        self.config = config

    @property
    def mode(self) -> DataMode:
        return DataMode.SYNC

    async def write(self, data: T, *args, **kwargs) -> T:
        # just return the data for now
        return data


@inject
def get_data_sink(config: BaseDataSinkConfig = Depends(get_data_sink_config)) -> BaseDataSink:
    return BaseDataSink(config)
