from functools import lru_cache

from pydantic_settings import BaseSettings


class BaseDataTriggerConfig(BaseSettings):
    pass


@lru_cache
def get_data_trigger_config() -> BaseDataTriggerConfig:
    return BaseDataTriggerConfig()
