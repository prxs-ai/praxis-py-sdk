from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    TWEETSCOUT_API_KEY: str = ""


@lru_cache
def get_settings():
    return Settings()
