from typing import Any, Generic, TypeVar

from base_provider.abc import AbstractDataSink
from base_provider.sink.config import BaseDataSinkConfig

T = TypeVar("T")


class BaseDataSink(AbstractDataSink[T], Generic[T]):
    """Base implementation of data sink."""

    def __init__(self, config: BaseDataSinkConfig):
        self.config = config

    async def write(self, data: T) -> None:
        pass


def get_data_sink(config: BaseDataSinkConfig) -> BaseDataSink:
    return BaseDataSink(config)
