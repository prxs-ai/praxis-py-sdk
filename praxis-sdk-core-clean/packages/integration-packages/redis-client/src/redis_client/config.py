from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int


@lru_cache
def get_settings():
    return Settings()
