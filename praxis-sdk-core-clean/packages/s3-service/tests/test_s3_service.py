import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import UploadFile
from botocore.exceptions import ClientError
import pytest_asyncio

with patch("s3_service.config.Settings") as mock_settings:
    mock_settings.return_value = MagicMock(
        infrastructure=MagicMock(
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
def mock_upload_file():
    file = MagicMock(spec=UploadFile)
    file.file = MagicMock()
    return file


@pytest_asyncio.fixture
async def s3_service():
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock()

    with patch("s3_service.main.aioboto3") as mock_aioboto3:
        mock_session = MagicMock()
        mock_session.client.return_value = mock_client
        mock_aioboto3.Session.return_value = mock_session

        service = S3Service("test-bucket")
        service.s3_client = mock_client
        yield service


def test_init_invalid_bucket_name():
    with pytest.raises(ValueError, match="Invalid bucket name"):
        S3Service("invalid_bucket_name!")


def test_init_valid_bucket_name():
    service = S3Service("valid-bucket")
    assert service.bucket_name == "test-prefix-valid-bucket"
    assert service.s3_bucket_url == "https://s3.example.com/test-prefix-valid-bucket"


@pytest.mark.asyncio
async def test_context_manager():
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock()

    with patch("s3_service.main.aioboto3") as mock_aioboto3:
        mock_session = MagicMock()
        mock_session.client.return_value = mock_client
        mock_aioboto3.Session.return_value = mock_session

        async with S3Service("test-bucket") as service:
            assert isinstance(service, S3Service)
        mock_client.__aexit__.assert_awaited_once()


@pytest.mark.asyncio
async def test_ensure_bucket_exists_exists(s3_service):
    s3_service.s3_client.head_bucket = AsyncMock()
    await s3_service._ensure_bucket_exists()
    s3_service.s3_client.head_bucket.assert_awaited_once_with(Bucket="test-prefix-test-bucket")


@pytest.mark.asyncio
async def test_ensure_bucket_exists_create(s3_service):
    s3_service.s3_client.head_bucket = AsyncMock(side_effect=ClientError(
        {"Error": {"Code": "404"}}, "head_bucket"
    ))
    s3_service.s3_client.create_bucket = AsyncMock()
    await s3_service._ensure_bucket_exists()
    s3_service.s3_client.create_bucket.assert_awaited_once_with(Bucket="test-prefix-test-bucket")


@pytest.mark.asyncio
async def test_ensure_bucket_exists_error(s3_service):
    s3_service.s3_client.head_bucket = AsyncMock(side_effect=ClientError(
        {"Error": {"Code": "403"}}, "head_bucket"
    ))
    with pytest.raises(Exception):
        await s3_service._ensure_bucket_exists()


@pytest.mark.asyncio
async def test_upload_file(s3_service, mock_upload_file):
    s3_service.s3_client.upload_fileobj = AsyncMock()
    result = await s3_service.upload_file(mock_upload_file, "test-key")
    assert result == "https://s3.example.com/test-prefix-test-bucket/test-key"
    s3_service.s3_client.upload_fileobj.assert_awaited_once()


@pytest.mark.asyncio
async def test_upload_file_error(s3_service, mock_upload_file):
    s3_service.s3_client.upload_fileobj = AsyncMock(side_effect=ClientError(
        {"Error": {"Code": "500"}}, "upload_fileobj"
    ))
    with pytest.raises(Exception, match="Uploading file error"):
        await s3_service.upload_file(mock_upload_file, "test-key")


@pytest.mark.asyncio
async def test_delete_file(s3_service):
    s3_service.s3_client.delete_object = AsyncMock()
    await s3_service.delete_file("test-key")
    s3_service.s3_client.delete_object.assert_awaited_once_with(
        Bucket="test-prefix-test-bucket", Key="test-key"
    )


@pytest.mark.asyncio
async def test_upload_file_bytes(s3_service):
    s3_service.s3_client.put_object = AsyncMock()
    result = await s3_service.upload_file_bytes("test-key", b"test-data", "text/plain")
    assert result == "https://s3.example.com/test-prefix-test-bucket/test-key"
    s3_service.s3_client.put_object.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_files(s3_service):
    s3_service.s3_client.list_objects_v2 = AsyncMock(return_value={
        "Contents": [{"Key": "file1"}, {"Key": "file2"}]
    })
    result = await s3_service.list_files("prefix")
    assert result == ["file1", "file2"]
    s3_service.s3_client.list_objects_v2.assert_awaited_once_with(
        Bucket="test-prefix-test-bucket", Prefix="prefix"
    )


@pytest.mark.asyncio
async def test_get_file_bytes(s3_service):
    mock_body = MagicMock()
    mock_body.read = AsyncMock(return_value=b"file-content")
    s3_service.s3_client.get_object = AsyncMock(return_value={"Body": mock_body})
    result = await s3_service.get_file_bytes("test-key")
    assert result == b"file-content"


@pytest.mark.asyncio
async def test_get_s3_service():
    with patch("s3_service.main.S3Service") as mock_service:
        mock_service.return_value.__aenter__.return_value = "test-service"
        result = await get_s3_service("test-bucket")
        assert result == "test-service"


@pytest.mark.asyncio
async def test_s3_service_dependency():
    with patch("s3_service.main.S3Service") as mock_service:
        mock_service.return_value.__aenter__.return_value = "test-service"
        dep = s3_service_dependency("test-bucket")
        result = await dep()
        assert result == "test-service"
