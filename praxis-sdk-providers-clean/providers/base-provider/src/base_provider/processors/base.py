from typing import Any, Generic, TypeVar

from base_provider.abc import AbstractDataProcessor
from base_provider.processors.config import BaseDataProcessorConfig, get_data_processor_config
from fast_depends import Depends, inject

T = TypeVar("T")
U = TypeVar("U")


class BaseDataProcessor(AbstractDataProcessor[T, U], Generic[T, U]):
    """Base implementation of data processor."""

    def __init__(self, config: BaseDataProcessorConfig):
        self.config = config

    async def process(self, data: T, **filters) -> U:

        return data  # type: ignore


@inject
def get_data_processor(config: BaseDataProcessorConfig = Depends(get_data_processor_config)) -> BaseDataProcessor:
    return BaseDataProcessor(config)
