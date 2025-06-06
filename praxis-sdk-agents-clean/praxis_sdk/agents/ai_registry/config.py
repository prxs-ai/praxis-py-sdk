from functools import lru_cache

import pydantic
from pydantic_settings import BaseSettings, SettingsConfigDict


class AiRegistryEndpoints(BaseSettings):
    find_agents: str = "/agents/find"
    find_tools: str = "/tools/find"


class AiRegistryConfig(BaseSettings):
    url: str = pydantic.Field("localhost")
    timeout: int = pydantic.Field(10)
    endpoints: AiRegistryEndpoints = AiRegistryEndpoints()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AI_REGISTRY_",
        env_file_encoding="utf-8",
        extra=pydantic.Extra.ignore,
    )


@lru_cache
def get_ai_registry_config() -> AiRegistryConfig:
    return AiRegistryConfig()  # type: ignore[misc]
