from functools import lru_cache

from pydantic_settings import BaseSettings


class BaseDataSourceConfig(BaseSettings):
    pass


@lru_cache
def get_data_source_config() -> BaseDataSourceConfig:
    return BaseDataSourceConfig()
