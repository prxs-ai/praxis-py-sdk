from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    OPENAI_API_KEY: str
    OPEN_AI_MODEL: str
    OPENAI_EMBEDDING_MODEL: str


@lru_cache
def get_settings():
    return Settings()
