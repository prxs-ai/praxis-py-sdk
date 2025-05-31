from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    QDRANT_HOST: str
    QDRANT_PORT: int
    VECTOR_DIMENSION: int


@lru_cache
def get_settings():
    return Settings()