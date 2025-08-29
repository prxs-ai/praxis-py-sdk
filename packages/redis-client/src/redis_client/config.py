from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    REDIS_HOST: str = 'localhost'
    REDIS_PORT: int = 6379
    REDIS_DB: int = 1


@lru_cache
def get_settings():
    return Settings()
