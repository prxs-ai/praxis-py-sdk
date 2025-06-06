from functools import lru_cache

import pydantic
from pydantic_settings import BaseSettings, SettingsConfigDict


class CardConfig(BaseSettings):
    name: str = "base-agent"
    version: str = "0.0.5"
    description: str = "This is a base agent. It provides a base implementation for all other agents."

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AGENT_CARD_",
        env_file_encoding="utf-8",
        extra=pydantic.Extra.ignore,
    )


@lru_cache
def get_card_config() -> CardConfig:
    return CardConfig()
