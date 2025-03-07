from functools import lru_cache

from pydantic_settings import BaseSettings


class BasicAgentConfig(BaseSettings):
    system_prompt: str = "Act as a helpful assistant. You are given a task to complete."

    agents: dict[str, str] = {}


@lru_cache
def get_agent_config() -> BasicAgentConfig:
    return BasicAgentConfig()
