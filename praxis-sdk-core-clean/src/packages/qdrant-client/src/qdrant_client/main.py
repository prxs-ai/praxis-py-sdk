import asyncio
import logging
from typing import Collection, Optional

from qdrant_client import QdrantClient, AsyncQdrantClient
from qdrant_client.http.models import VectorParams, Distance
from qdrant_client.config import get_settings

settings = get_settings()


def get_qdrant_client(*args, **kwargs) -> QdrantClient:
    return QdrantClientPackage(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)


class QdrantClientPackage(QdrantClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def create_new_collection(self, collection_name: str) -> None:
        # Create collection if it doesn't exist
        if not self.collection_exists(collection_name):
            self.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=settings.VECTOR_DIMENSION,
                    distance=Distance.COSINE
                )
            )
