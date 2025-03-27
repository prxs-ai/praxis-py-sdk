from typing import Any, Generic, TypeVar

from base_provider.abc import AbstractDataProcessor
from base_provider.processor.config import BaseDataProcessorConfig

T = TypeVar("T")
U = TypeVar("U")


class BaseDataProcessor(AbstractDataProcessor[T, U], Generic[T, U]):
    """Base implementation of data processor."""

    def __init__(self, config: BaseDataProcessorConfig):
        self.config = config

    async def process(self, data: T, filters: dict[str, Any]) -> U:

        return data  # type: ignore


def get_data_processor(config: BaseDataProcessorConfig) -> BaseDataProcessor:
    return BaseDataProcessor(config)
