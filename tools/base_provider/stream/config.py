from functools import lru_cache

from pydantic_settings import BaseSettings


class BaseDataStreamConfig(BaseSettings):
    pass


@lru_cache
def get_data_stream_config() -> BaseDataStreamConfig:
    return BaseDataStreamConfig()
