from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = "6688"
    VECTOR_DIMENSION: int = "1"


@lru_cache
def get_settings():
    return Settings()
