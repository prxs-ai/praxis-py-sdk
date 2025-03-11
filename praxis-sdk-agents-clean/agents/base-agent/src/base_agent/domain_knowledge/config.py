from functools import lru_cache

import pydantic
from pydantic_settings import BaseSettings, SettingsConfigDict


class LightRagEndpoints(BaseSettings):
    query: str = "/query"


class LightRagConfig(BaseSettings):
    light_rag_service_url: str = pydantic.Field("localhost")
    light_rag_port: int = pydantic.Field(9621)
    timeout: int = pydantic.Field(10)
    endpoints: LightRagEndpoints = LightRagEndpoints()

    @property
    def url(self) -> str:
        return f"http://{self.light_rag_service_url}:{self.light_rag_port}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="LIGHT_RAG_",
        env_file_encoding="utf-8",
        extra=pydantic.Extra.ignore,
    )


@lru_cache
def get_light_rag_config() -> LightRagConfig:
    return LightRagConfig()
