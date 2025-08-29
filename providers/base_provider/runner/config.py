from functools import lru_cache

from pydantic_settings import BaseSettings


class BaseDataRunnerConfig(BaseSettings):
    pass


@lru_cache
def get_data_runner_config() -> BaseDataRunnerConfig:
    return BaseDataRunnerConfig()
