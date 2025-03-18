import asyncio
from typing import Any

from lightrag import LightRAG, QueryParam
from lightrag.kg.shared_storage import initialize_pipeline_status
from lightrag.llm.ollama import ollama_embedding
from lightrag.llm.zhipu import zhipu_complete
from lightrag.utils import EmbeddingFunc

from base_agent.domain_knowledge.config import LightRagConfig


class LightRagClient:
    def __init__(self, config: LightRagConfig) -> None:
        self.rag = LightRAG(
            working_dir=config.working_dir,
            llm_model_func=zhipu_complete,
            llm_model_name=config.llm_model_name,
            llm_model_max_async=config.llm_model_max_async,
            llm_model_max_token_size=config.llm_model_max_token_size,
            enable_llm_cache_for_entity_extract=config.enable_llm_cache_for_entity_extract,
            embedding_func=EmbeddingFunc(
                embedding_dim=config.embedding_dim,
                max_token_size=config.embedding_max_token_size,
                func=lambda texts: ollama_embedding(
                    texts,
                    embed_model=config.embedding_model.name,
                    host=config.embedding_model.url,
                ),
            ),
            kv_storage=config.kv_storage,
            doc_status_storage=config.doc_status_storage,
            graph_storage=config.graph_storage,
            vector_storage=config.vector_storage,
            auto_manage_storages_states=config.auto_manage_storages_states,
        )

    async def initialize_rag(self) -> None:
        """
        Initialize the LightRAG instance with PostgreSQL as the storage backend.
        """

        await self.rag.initialize_storages()
        await initialize_pipeline_status()

    def query(self, query: str, mode: str = "naive") -> dict[str, Any]:
        """
        Synchronously query the LightRAG instance with the specified mode.
        """

        async def _async_query():
            param = QueryParam(mode=mode)
            result = await self.rag.aquery(query, param=param)
            return {"domain_knowledge": result}

        return asyncio.run(_async_query())


def light_rag_client(config: LightRagConfig) -> LightRagClient:
    client = LightRagClient(config=config)
    asyncio.run(client.initialize_rag())
    return client
