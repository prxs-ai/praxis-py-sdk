import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from botocore.exceptions import ClientError
from fastapi import UploadFile

with patch("s3_service.config.Settings") as mock_settings:
    mock_settings.return_value = AsyncMock(
        infrastructure=AsyncMock(
            s3_base_url="https://s3.example.com",
            s3_bucket_prefix="test-prefix",
            S3_ACCESS_KEY="test-access-key",
            S3_SECRET="test-secret-key",
            S3_REGION="test-region"
        )
    )
    with patch("s3_service.main.S3Service") as mock_aioboto3:
        from s3_service.main import S3Service, get_s3_service, s3_service_dependency


@pytest.fixture
def s3_service():
    service = S3Service("test-bucket")
    service.s3_client = AsyncMock()
    return service


@pytest.fixture
def mock_upload_file():
    mock = MagicMock(spec=UploadFile)
    mock.filename = "test.txt"
    mock.file.read = AsyncMock(return_value=b"test data")
    return mock


@patch("s3_service.main.settings")
def test_init_valid_bucket_name(mock_settings):
    mock_settings.infrastructure.s3_bucket_prefix = "prefix-"
    mock_settings.infrastructure.s3_base_url = "https://s3.example.com"
    service = S3Service("mybucket")
    assert service.bucket_name == "prefix-mybucket"
    assert service.s3_bucket_url == "https://s3.example.com/prefix-mybucket"


@patch("s3_service.main.settings")
def test_init_without_prefix(mock_settings):
    mock_settings.infrastructure.s3_bucket_prefix = ""
    mock_settings.infrastructure.s3_base_url = "https://s3.example.com"
    service = S3Service("mybucket")
    assert service.bucket_name == "mybucket"
    assert service.s3_bucket_url == "https://s3.example.com/mybucket"


@pytest.mark.asyncio
async def test_upload_file_success(s3_service, mock_upload_file):
    s3_service.s3_client.put_object = AsyncMock()
    url = await s3_service.upload_file(mock_upload_file, "test-key")
    assert url.endswith("test-key")
    s3_service.s3_client.put_object.assert_awaited_once()


@pytest.mark.asyncio
async def test_upload_file_attribute_error(s3_service):
    bad_file = AsyncMock(spec=UploadFile)
    del bad_file.file
    with pytest.raises(Exception, match="Uploading file error"):
        await s3_service.upload_file(bad_file, "test-key")


@pytest.mark.asyncio
async def test_get_file_bytes_success(s3_service):
    mock_body = AsyncMock()
    mock_body.read = AsyncMock(return_value=b"file data")
    s3_service.s3_client.get_object = AsyncMock(return_value={"Body": mock_body})

    data = await s3_service.get_file_bytes("test-key")
    assert data == b"file data"


@pytest.mark.asyncio
async def test_get_file_bytes_error(s3_service):
    mock_body = AsyncMock()
    mock_body.read = AsyncMock(side_effect=Exception("read error"))
    s3_service.s3_client.get_object = AsyncMock(return_value={"Body": mock_body})
    with pytest.raises(Exception, match="Failed to get file bytes"):
        await s3_service.get_file_bytes("test-key")


@pytest.mark.asyncio
async def test_ensure_bucket_exists_bucket_exists(s3_service):
    s3_service.s3_client.head_bucket = AsyncMock()
    await s3_service._ensure_bucket_exists()
    s3_service.s3_client.head_bucket.assert_awaited_once_with(Bucket=s3_service.bucket_name)


@pytest.mark.asyncio
async def test_ensure_bucket_exists_creates_bucket(s3_service):
    s3_service.s3_client.head_bucket = AsyncMock(
        side_effect=ClientError({"Error": {"Code": "404"}}, "head_bucket")
    )
    s3_service.s3_client.create_bucket = AsyncMock()
    await s3_service._ensure_bucket_exists()
    s3_service.s3_client.create_bucket.assert_awaited_once_with(Bucket=s3_service.bucket_name)


@pytest.mark.asyncio
async def test_ensure_bucket_exists_unhandled_error(s3_service):
    s3_service.s3_client.head_bucket = AsyncMock(
        side_effect=ClientError({"Error": {"Code": "500"}}, "head_bucket")
    )
    with pytest.raises(ClientError):
        await s3_service._ensure_bucket_exists()


@pytest.mark.asyncio
async def test_create_bucket_error(s3_service):
    s3_service.s3_client.head_bucket = AsyncMock(
        side_effect=ClientError({"Error": {"Code": "404"}}, "head_bucket")
    )
    s3_service.s3_client.create_bucket = AsyncMock(
        side_effect=ClientError({"Error": {"Code": "403"}}, "create_bucket")
    )
    with pytest.raises(ClientError):
        await s3_service._ensure_bucket_exists()
