from typing import Any, Generic, TypeVar

from base_provider.abc import AbstractDataSource
from base_provider.source.config import BaseDataSourceConfig

T = TypeVar("T")


class BaseDataSource(AbstractDataSource[T], Generic[T]):
    """Base implementation of data Source."""

    def __init__(self, config: BaseDataSourceConfig):
        self.config = config

    async def fetch(self, *args, **kwargs) -> list[T]:
        return [{"data": "example"}]


def get_data_source(config: BaseDataSourceConfig) -> BaseDataSource:
    return BaseDataSource(config)
