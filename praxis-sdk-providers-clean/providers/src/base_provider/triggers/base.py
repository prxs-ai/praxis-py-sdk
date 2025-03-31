from typing import Generic, TypeVar

from base_provider.abc import AbstractDataTrigger
from base_provider.triggers.config import BaseDataTriggerConfig, get_data_trigger_config
from fast_depends import Depends, inject

T = TypeVar("T")


class BaseDataTrigger(AbstractDataTrigger[T], Generic[T]):
    """Base implementation of data Trigger."""

    def __init__(self, config: BaseDataTriggerConfig):
        self.config = config

    async def trigger(self, *args, **kwargs) -> T:
        raise NotImplementedError


@inject
def get_data_trigger(config: BaseDataTriggerConfig = Depends(get_data_trigger_config)) -> BaseDataTrigger:
    return BaseDataTrigger(config)
