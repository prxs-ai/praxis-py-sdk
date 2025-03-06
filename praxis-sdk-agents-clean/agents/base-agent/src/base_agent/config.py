from functools import lru_cache

from pydantic_settings import BaseSettings


class BasicAgentConfig(BaseSettings):
    agents: dict[str, str] = {}


@lru_cache
def get_agent_config() -> BasicAgentConfig:
    return BasicAgentConfig()
