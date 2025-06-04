import pytest
from unittest.mock import MagicMock, patch, call
from qdrant_client.models import VectorParams, Distance, PointStruct, ScoredPoint
from qdrant_client_custom.main import QdrantClientPackage, get_qdrant_client, QdrantClient


@pytest.fixture
def mock_qdrant_client():
    return MagicMock(spec=QdrantClient)


@pytest.fixture
def qdrant_package(mock_qdrant_client):
    with patch('qdrant_client_custom.QdrantClient.__init__', return_value=None):
        client = QdrantClientPackage(host="localhost", port=6333)
        client._client = mock_qdrant_client
        return client


def test_get_qdrant_client():
    mock_settings = MagicMock()
    mock_settings.QDRANT_HOST = "test_host"
    mock_settings.QDRANT_PORT = 1234
    mock_settings.VECTOR_DIMENSION = 384

    with patch('qdrant_client_custom.main.get_settings', return_value=mock_settings), \
            patch('qdrant_client_custom.main.QdrantClientPackage') as mock_client:
        result = get_qdrant_client()
        mock_client.assert_called_once_with(host="test_host", port=1234)
        assert result == mock_client.return_value


def test_client_initialization():
    with patch('qdrant_client_custom.QdrantClient.__init__') as mock_init:
        mock_init.return_value = None
        client = QdrantClientPackage(host="test_host", port=1234, api_key="test_key")
        mock_init.assert_called_once_with(host="test_host", port=1234, api_key="test_key")


def test_create_new_collection_new(qdrant_package, mock_qdrant_client):
    mock_qdrant_client.collection_exists.return_value = False

    qdrant_package.create_new_collection("test_collection")

    mock_qdrant_client.collection_exists.assert_called_once_with("test_collection")
    mock_qdrant_client.create_collection.assert_called_once_with(
        collection_name="test_collection",
        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
    )


def test_create_new_collection_exists(qdrant_package, mock_qdrant_client):
    mock_qdrant_client.collection_exists.return_value = True

    qdrant_package.create_new_collection("existing_collection")

    mock_qdrant_client.collection_exists.assert_called_once_with("existing_collection")
    mock_qdrant_client.create_collection.assert_not_called()


def test_upsert_points(qdrant_package, mock_qdrant_client):
    points = [
        PointStruct(id=1, vector=[0.1, 0.2], payload={"key": "value"}),
        PointStruct(id=2, vector=[0.3, 0.4], payload={"key": "value2"})
    ]

    qdrant_package.upsert_points("test_collection", points)

    mock_qdrant_client.upsert.assert_called_once_with(
        collection_name="test_collection",
        points=points,
        wait=True
    )


def test_search_points(qdrant_package, mock_qdrant_client):
    mock_result = [
        ScoredPoint(id=1, score=0.95, payload={"key": "value"}, version=1),
        ScoredPoint(id=2, score=0.85, payload={"key": "value2"}, version=1)
    ]
    mock_qdrant_client.search.return_value = mock_result

    query_vector = [0.5, 0.5]
    result = qdrant_package.search_points(
        collection_name="test_collection",
        query_vector=query_vector,
        limit=2
    )

    mock_qdrant_client.search.assert_called_once_with(
        collection_name="test_collection",
        query_vector=query_vector,
        limit=2,
        with_vectors=False,
        with_payload=True
    )
    assert result == mock_result


def test_delete_collection(qdrant_package, mock_qdrant_client):
    qdrant_package.delete_collection("test_collection")
    mock_qdrant_client.delete_collection.assert_called_once_with("test_collection")


def test_delete_points(qdrant_package, mock_qdrant_client):
    qdrant_package.delete_points("test_collection", [1, 2, 3])
    mock_qdrant_client.delete.assert_called_once_with(
        collection_name="test_collection",
        points_selector=[1, 2, 3],
        wait=True
    )


def test_collection_exists(qdrant_package, mock_qdrant_client):
    mock_qdrant_client.collection_exists.return_value = True
    assert qdrant_package.collection_exists("test_collection") is True
    mock_qdrant_client.collection_exists.assert_called_once_with("test_collection")


def test_get_collection_info(qdrant_package, mock_qdrant_client):
    mock_info = {"vectors_count": 100, "segments_count": 5}
    mock_qdrant_client.get_collection.return_value = mock_info

    result = qdrant_package.get_collection_info("test_collection")

    mock_qdrant_client.get_collection.assert_called_once_with("test_collection")
    assert result == mock_info


def test_batch_upload(qdrant_package, mock_qdrant_client):
    points_batch = [
        [PointStruct(id=1, vector=[0.1, 0.2])],
        [PointStruct(id=2, vector=[0.3, 0.4])]
    ]

    qdrant_package.batch_upload("test_collection", points_batch)

    assert mock_qdrant_client.upsert.call_count == 2
    mock_qdrant_client.upsert.assert_has_calls([
        call(collection_name="test_collection", points=points_batch[0], wait=True),
        call(collection_name="test_collection", points=points_batch[1], wait=True)
    ])


def test_search_points_error(qdrant_package, mock_qdrant_client):
    mock_qdrant_client.search.side_effect = Exception("Search error")

    with pytest.raises(Exception, match="Search error"):
        qdrant_package.search_points("test_collection", [0.5, 0.5])