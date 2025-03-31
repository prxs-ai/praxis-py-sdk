from typing import Generic, TypeVar

from base_provider.abc import AbstractDataTrigger
from base_provider.triggers.config import BaseDataTriggerConfig

T = TypeVar("T")


class BaseDataTrigger(AbstractDataTrigger[T], Generic[T]):
    """Base implementation of data Trigger."""

    def __init__(self, config: BaseDataTriggerConfig):
        self.config = config

    async def trigger(self, *args, **kwargs) -> T:
        raise NotImplementedError


def get_data_trigger(config: BaseDataTriggerConfig) -> BaseDataTrigger:
    return BaseDataTrigger(config)
