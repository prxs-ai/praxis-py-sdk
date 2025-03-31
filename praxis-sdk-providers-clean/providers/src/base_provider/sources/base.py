from typing import Generic, TypeVar

from base_provider.abc import AbstractDataSource
from base_provider.sources.config import BaseDataSourceConfig, get_data_source_config
from fast_depends import Depends, inject

T = TypeVar("T")


class BaseDataSource(AbstractDataSource[T], Generic[T]):
    """Base implementation of data Source."""

    def __init__(self, config: BaseDataSourceConfig):
        self.config = config

    async def fetch(self, *args, **kwargs) -> list[T]:
        return []


@inject
def get_data_source(config: BaseDataSourceConfig = Depends(get_data_source_config)) -> BaseDataSource:
    return BaseDataSource(config)
