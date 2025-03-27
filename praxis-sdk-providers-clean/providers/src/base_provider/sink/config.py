from functools import lru_cache

from pydantic_settings import BaseSettings


class BaseDataSinkConfig(BaseSettings):
    pass


@lru_cache
def get_data_sink_config() -> BaseDataSinkConfig:
    return BaseDataSinkConfig()
