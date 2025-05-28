from functools import lru_cache

import pydantic
from pydantic_settings import BaseSettings, SettingsConfigDict


class KnowledgeBaseEndpoints(BaseSettings):
    query: str = "/knowledge/query"
    insert: str = "/knowledge/insert"


class Retries(BaseSettings):
    stop_attempts: int = 3
    wait_multiplier: int = 1
    wait_min: int = 4
    wait_max: int = 10


class LightRagConfig(BaseSettings):
    host: str = pydantic.Field("localhost")
    port: int = pydantic.Field(8000)
    timeout: int = pydantic.Field(10)
    endpoints: KnowledgeBaseEndpoints = KnowledgeBaseEndpoints()

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="KNOWLEDGE_BASE_",
        env_file_encoding="utf-8",
        extra=pydantic.Extra.ignore,
    )


@lru_cache
def get_light_rag_config() -> LightRagConfig:
    return LightRagConfig()


retries: Retries = Retries()
