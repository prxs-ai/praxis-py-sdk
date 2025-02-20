from functools import lru_cache

from pydantic import BaseModel


class BasicAgentConfig(BaseModel):
    group_name: str = "agent.entrypoint"
    target_entrypoint: str = "target"
    default_entrypoint: str = "basic"


@lru_cache
def get_agent_config() -> BasicAgentConfig:
    return BasicAgentConfig()
