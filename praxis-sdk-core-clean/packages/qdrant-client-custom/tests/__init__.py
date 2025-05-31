import pytest
from unittest.mock import Mock, patch
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
from qdrant_client_custom.client import QdrantClientPackage, get_qdrant_client


@pytest.fixture
def mock_settings():
    class MockSettings:
        QDRANT_HOST = "localhost"
        QDRANT_PORT = 6333
        VECTOR_DIMENSION = 128

    return MockSettings()


@pytest.fixture
def qdrant_client(mock_settings):
    with patch("qdrant_client_custom.client.get_settings", return_value=mock_settings):
        client = get_qdrant_client()
        yield client


@pytest.mark.asyncio
async def test_get_qdrant_client(mock_settings):
    with patch("qdrant_client_custom.client.get_settings", return_value=mock_settings):
        client = get_qdrant_client()
        assert isinstance(client, QdrantClientPackage)
        assert client._client._host == mock_settings.QDRANT_HOST
        assert client._client._port == mock_settings.QDRANT_PORT


@pytest.mark.asyncio
async def test_create_new_collection_exists(qdrant_client, mocker):
    mocker.patch.object(qdrant_client, "collection_exists", return_value=True)
    mock_create_collection = mocker.patch.object(qdrant_client, "create_collection")

    qdrant_client.create_new_collection("test_collection")
    mock_create_collection.assert_not_called()


@pytest.mark.asyncio
async def test_create_new_collection_not_exists(qdrant_client, mocker):
    mocker.patch.object(qdrant_client, "collection_exists", return_value=False)
    mock_create_collection = mocker.patch.object(qdrant_client, "create_collection")

    qdrant_client.create_new_collection("test_collection")
    mock_create_collection.assert_called_once_with(
        collection_name="test_collection",
        vectors_config=VectorParams(
            size=qdrant_client._client._settings.VECTOR_DIMENSION,
            distance=Distance.COSINE
        )
    )
