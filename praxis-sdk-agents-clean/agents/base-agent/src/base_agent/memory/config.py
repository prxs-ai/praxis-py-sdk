from functools import lru_cache

from pydantic import Extra, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Redis(BaseSettings):
    host: str = Field("localhost")
    port: int = Field(6379)
    db: int = Field(0)

    @property
    def url(self) -> str:
        return f"redis://{self.host}:{self.port}/{self.db}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="REDIS_CELERY_",
        env_file_encoding="utf-8",
        extra=Extra.ignore,
    )


class MemoryConfig(BaseSettings):
    collection_name: str = Field("memory")
    embedding_model_dims: int = Field(1536)
    redis: Redis = Redis()

    @property
    def mem0_config(self) -> dict:
        return {
            "vector_store": {
                "provider": "redis",
                "config": {
                    "collection_name": self.collection_name,
                    "embedding_model_dims": self.embedding_model_dims,
                    "redis_url": self.redis.url,
                },
            },
            "version": "v1.1",
        }


@lru_cache
def get_memory_config() -> MemoryConfig:
    return MemoryConfig()
