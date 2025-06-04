import pytest
from unittest.mock import AsyncMock, patch, Mock
from fastapi import UploadFile
from botocore.exceptions import ClientError
from loguru import logger
from s3_service import S3Service, get_s3_service, s3_service_dependency


@pytest.fixture
def mock_settings():
    class MockSettings:
        class Infrastructure:
            s3_base_url = "https://s3.example.com"
            s3_bucket_prefix = "test-prefix"
            s3_access_key = "access_key"
            s3_secret_key = "secret_key"

        infrastructure = Infrastructure()

    return MockSettings()


@pytest.fixture
def bucket_name():
    return "valid-bucket"


@pytest.mark.asyncio
async def test_s3_service_init_valid_bucket(mock_settings, mocker):
    mocker.patch("s3_service.get_settings", return_value=mock_settings)
    service = S3Service("valid-bucket")
    assert service.bucket_name == "test-prefix-valid-bucket"
    assert service.s3_bucket_url == "https://s3.example.com/test-prefix-valid-bucket"


@pytest.mark.asyncio
async def test_s3_service_init_invalid_bucket(mock_settings, mocker):
    mocker.patch("s3_service.get_settings", return_value=mock_settings)
    with pytest.raises(ValueError, match="Invalid bucket name: invalid_bucket!"):
        S3Service("invalid_bucket!")


@pytest.mark.asyncio
async def test_ensure_bucket_exists(mock_settings, mocker, bucket_name):
    mocker.patch("s3_service.get_settings", return_value=mock_settings)
    mock_s3_client = AsyncMock()
    mock_s3_client.head_bucket.return_value = {}
    mocker.patch("aioboto3.Session.client", AsyncMock(return_value=mock_s3_client))

    async with S3Service(bucket_name) as service:
        await service._ensure_bucket_exists()
        mock_s3_client.head_bucket.assert_called_once_with(Bucket="test-prefix-valid-bucket")


@pytest.mark.asyncio
async def test_ensure_bucket_create_new(mock_settings, mocker, bucket_name):
    mocker.patch("s3_service.get_settings", return_value=mock_settings)
    mock_s3_client = AsyncMock()
    mock_s3_client.head_bucket.side_effect = ClientError({"Error": {"Code": "404"}}, "head_bucket")
    mock_s3_client.create_bucket.return_value = {}
    mocker.patch("aioboto3.Session.client", AsyncMock(return_value=mock_s3_client))
    mocker.patch.object(logger, "info")

    async with S3Service(bucket_name) as service:
        await service._ensure_bucket_exists()
        mock_s3_client.create_bucket.assert_called_once_with(Bucket="test-prefix-valid-bucket")
        logger.info.assert_called_once_with("Bucket 'test-prefix-valid-bucket' does not exist. Creating bucket.")


@pytest.mark.asyncio
async def test_ensure_bucket_create_failure(mock_settings, mocker, bucket_name):
    mocker.patch("s3_service.get_settings", return_value=mock_settings)
    mock_s3_client = AsyncMock()
    mock_s3_client.head_bucket.side_effect = ClientError({"Error": {"Code": "404"}}, "head_bucket")
    mock_s3_client.create_bucket.side_effect = ClientError({"Error": {"Code": "500"}}, "create_bucket")
    mocker.patch("aioboto3.Session.client", AsyncMock(return_value=mock_s3_client))
    mocker.patch.object(logger, "exception")

    async with S3Service(bucket_name) as service:
        with pytest.raises(Exception, match="Creation bucket error:"):
            await service._ensure_bucket_exists()
        logger.exception.assert_called_once_with("Failed to create bucket 'test-prefix-valid-bucket'.")


@pytest.mark.asyncio
async def test_upload_file_success(mock_settings, mocker, bucket_name):
    mocker.patch("s3_service.get_settings", return_value=mock_settings)
    mock_s3_client = AsyncMock()
    mock_s3_client.upload_fileobj.return_value = {}
    mocker.patch("aioboto3.Session.client", AsyncMock(return_value=mock_s3_client))
    mock_file = Mock(spec=UploadFile)
    mock_file.file = Mock()

    async with S3Service(bucket_name) as service:
        result = await service.upload_file(mock_file, "test.txt")
        assert result == "https://s3.example.com/test-prefix-valid-bucket/test.txt"
        mock_s3_client.upload_fileobj.assert_called_once_with(
            mock_file.file,
            "test-prefix-valid-bucket",
            "test.txt",
            ExtraArgs={"ACL": "public-read"}
        )


@pytest.mark.asyncio
async def test_upload_file_failure(mock_settings, mocker, bucket_name):
    mocker.patch("s3_service.get_settings", return_value=mock_settings)
    mock_s3_client = AsyncMock()
    mock_s3_client.upload_fileobj.side_effect = ClientError({"Error": {"Code": "500"}}, "upload_fileobj")
    mocker.patch("aioboto3.Session.client", AsyncMock(return_value=mock_s3_client))
    mock_file = Mock(spec=UploadFile)
    mock_file.file = Mock()
    mocker.patch.object(logger, "exception")

    async with S3Service(bucket_name) as service:
        with pytest.raises(Exception, match="Uploading file error:"):
            await service.upload_file(mock_file, "test.txt")
        logger.exception.assert_called_once_with("Failed to upload file to S3.")


@pytest.mark.asyncio
async def test_delete_file_success(mock_settings, mocker, bucket_name):
    mocker.patch("s3_service.get_settings", return_value=mock_settings)
    mock_s3_client = AsyncMock()
    mock_s3_client.delete_object.return_value = {}
    mocker.patch("aioboto3.Session.client", AsyncMock(return_value=mock_s3_client))

    async with S3Service(bucket_name) as service:
        await service.delete_file("test.txt")
        mock_s3_client.delete_object.assert_called_once_with(Bucket="test-prefix-valid-bucket", Key="test.txt")


@pytest.mark.asyncio
async def test_delete_file_failure(mock_settings, mocker, bucket_name):
    mocker.patch("s3_service.get_settings", return_value=mock_settings)
    mock_s3_client = AsyncMock()
    mock_s3_client.delete_object.side_effect = ClientError({"Error": {"Code": "500"}}, "delete_object")
    mocker.patch("aioboto3.Session.client", AsyncMock(return_value=mock_s3_client))
    mocker.patch.object(logger, "exception")

    async with S3Service(bucket_name) as service:
        with pytest.raises(Exception, match="Deleting file error:"):
            await service.delete_file("test.txt")
        logger.exception.assert_called_once_with("Failed to delete file from S3.")


@pytest.mark.asyncio
async def test_get_file_url(mock_settings, mocker, bucket_name):
    mocker.patch("s3_service.get_settings", return_value=mock_settings)
    async with S3Service(bucket_name) as service:
        result = service.get_file_url("test.txt")
        assert result == "https://s3.example.com/test-prefix-valid-bucket/test.txt"
