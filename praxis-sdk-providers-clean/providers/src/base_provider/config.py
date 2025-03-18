from functools import lru_cache

from pydantic_settings import BaseSettings


class BasicProviderConfig(BaseSettings):
    pass


@lru_cache
def get_provider_config() -> BasicProviderConfig:
    return BasicProviderConfig()
