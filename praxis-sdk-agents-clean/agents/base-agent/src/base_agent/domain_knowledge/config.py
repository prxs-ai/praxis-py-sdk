from functools import lru_cache

import pydantic
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmbeddingModel(BaseSettings):
    name: str = Field("bge-m3")
    host: str = Field("localhost")
    port: int = Field(11434)

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


class LightRagConfig(BaseSettings):
    working_dir: str = Field("./lightrag_working_dir")
    llm_model_name: str = Field("glm-4-flashx")

    # ---- Embedding Model -----#
    embedding_model: EmbeddingModel = EmbeddingModel()

    llm_model_max_async: int = Field(4)
    llm_model_max_token_size: int = Field(32768)
    enable_llm_cache_for_entity_extract: bool = Field(True)
    embedding_dim: int = Field(1024)
    embedding_max_token_size: int = Field(8192)
    kv_storage: str = Field("PGKVStorage")
    doc_status_storage: str = Field("PGDocStatusStorage")
    graph_storage: str = Field("PGGraphStorage")
    vector_storage: str = Field("PGVectorStorage")
    auto_manage_storages_states: bool = Field(False)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="LIGHT_RAG_",
        env_file_encoding="utf-8",
        extra=pydantic.Extra.ignore,
    )


@lru_cache
def get_light_rag_config() -> LightRagConfig:
    return LightRagConfig()
