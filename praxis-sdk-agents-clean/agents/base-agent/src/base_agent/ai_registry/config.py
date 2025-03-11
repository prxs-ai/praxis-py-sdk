from functools import lru_cache

import pydantic
from pydantic_settings import BaseSettings, SettingsConfigDict


class AiRegistryEndpoints(BaseSettings):
    find_agents: str = "/agents/find"
    find_tools: str = "/tools/find"


class AiRegistryConfig(BaseSettings):
    ai_registry_service_url: str = pydantic.Field("localhost")
    ai_registry_port: int = pydantic.Field(8000)
    timeout: int = pydantic.Field(10)
    endpoints: AiRegistryEndpoints = AiRegistryEndpoints()

    @property
    def url(self) -> str:
        return f"http://{self.ai_registry_service_url}:{self.ai_registry_port}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AI_REGISTRY_",
        env_file_encoding="utf-8",
        extra=pydantic.Extra.ignore,
    )


@lru_cache
def get_ai_registry_config() -> AiRegistryConfig:
    return AiRegistryConfig()
