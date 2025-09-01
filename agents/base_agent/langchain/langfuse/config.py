from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings


class BasicLangFuseConfig(BaseSettings):
    langfuse_secret_key: SecretStr
    langfuse_public_key: SecretStr
    langfuse_host: str


@lru_cache
def get_langfuse_config() -> BasicLangFuseConfig:
    return BasicLangFuseConfig()
