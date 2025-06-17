from functools import lru_cache

from pydantic_settings import BaseSettings


class BaseDataProcessorConfig(BaseSettings):
    pass


@lru_cache
def get_data_processor_config() -> BaseDataProcessorConfig:
    return BaseDataProcessorConfig()
