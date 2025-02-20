from functools import lru_cache

from pydantic_settings import BaseSettings


class AgentConfig(BaseSettings):
    group_name: str = "agent.entrypoint"
    entrypoint: str = "basic"


@lru_cache
def get_agent_config() -> AgentConfig:
    return AgentConfig()
