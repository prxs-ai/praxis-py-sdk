from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from qdrant_client_custom.config import get_settings

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
                    size=settings.VECTOR_DIMENSION, distance=Distance.COSINE
                ),
            )
