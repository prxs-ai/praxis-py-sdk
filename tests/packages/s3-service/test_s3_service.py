import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from botocore.exceptions import ClientError
from fastapi import UploadFile
import io

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


# Мокаем настройки до импорта
@pytest.fixture(autouse=True)
def mock_settings():
    with patch("s3_service.main.get_settings") as mock_get_settings:
        mock_settings = MagicMock()
        mock_settings.infrastructure.s3_base_url = "https://s3.example.com"
        mock_settings.infrastructure.s3_bucket_prefix = "test-prefix"
        mock_settings.infrastructure.s3_access_key = "test-access-key"
        mock_settings.infrastructure.s3_secret_key = "test-secret-key"
        mock_get_settings.return_value = mock_settings
        yield mock_settings


@pytest.fixture
def s3_service():
    from s3_service.main import S3Service
    service = S3Service("test-bucket")
    service.s3_client = AsyncMock()
    return service


@pytest.fixture
def mock_upload_file():
    mock = MagicMock(spec=UploadFile)
    mock.filename = "test.txt"
    mock.file = io.BytesIO(b"test data")
    return mock


def test_init_valid_bucket_name():
    """Тест инициализации с валидным именем bucket"""
    from s3_service.main import S3Service

    service = S3Service("mybucket")
    assert service.bucket_name == "test-prefix-mybucket"
    assert service.s3_bucket_url == "https://s3.example.com/test-prefix-mybucket"


def test_init_invalid_bucket_name():
    """Тест инициализации с невалидным именем bucket"""
    from s3_service.main import S3Service

    with pytest.raises(ValueError, match="Invalid bucket name"):
        S3Service("INVALID_BUCKET_NAME!")


def test_init_bucket_name_too_short():
    """Тест инициализации с коротким именем bucket"""
    from s3_service.main import S3Service

    with pytest.raises(ValueError, match="Invalid bucket name"):
        S3Service("ab")


def test_init_bucket_name_too_long():
    """Тест инициализации с длинным именем bucket"""
    from s3_service.main import S3Service

    long_name = "a" * 64
    with pytest.raises(ValueError, match="Invalid bucket name"):
        S3Service(long_name)


@pytest.mark.asyncio
async def test_context_manager_enter():
    """Тест входа в контекстный менеджер"""
    from s3_service.main import S3Service

    with patch("s3_service.main.aioboto3") as mock_aioboto3:
        mock_session = AsyncMock()
        mock_client = AsyncMock()
        mock_session.client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_aioboto3.Session.return_value = mock_session

        service = S3Service("test-bucket")

        # Мокаем _ensure_bucket_exists
        service._ensure_bucket_exists = AsyncMock()

        result = await service.__aenter__()

        assert result == service
        assert service.s3_client == mock_client
        service._ensure_bucket_exists.assert_awaited_once()


@pytest.mark.asyncio
async def test_context_manager_exit():
    """Тест выхода из контекстного менеджера"""
    from s3_service.main import S3Service

    service = S3Service("test-bucket")
    mock_client = AsyncMock()
    service.s3_client = mock_client

    await service.__aexit__(None, None, None)

    mock_client.__aexit__.assert_awaited_once_with(None, None, None)


@pytest.mark.asyncio
async def test_ensure_bucket_exists_success(s3_service):
    """Тест успешной проверки существования bucket"""
    s3_service.s3_client.head_bucket = AsyncMock()

    await s3_service._ensure_bucket_exists()

    s3_service.s3_client.head_bucket.assert_awaited_once_with(Bucket="test-prefix-test-bucket")


@pytest.mark.asyncio
async def test_ensure_bucket_exists_creates_bucket(s3_service):
    """Тест создания bucket при его отсутствии"""
    s3_service.s3_client.head_bucket = AsyncMock(
        side_effect=ClientError({"Error": {"Code": "404"}}, "HeadBucket")
    )
    s3_service.s3_client.create_bucket = AsyncMock()

    await s3_service._ensure_bucket_exists()

    s3_service.s3_client.create_bucket.assert_awaited_once_with(Bucket="test-prefix-test-bucket")


@pytest.mark.asyncio
async def test_ensure_bucket_exists_create_error(s3_service):
    """Тест ошибки при создании bucket"""
    s3_service.s3_client.head_bucket = AsyncMock(
        side_effect=ClientError({"Error": {"Code": "404"}}, "HeadBucket")
    )
    s3_service.s3_client.create_bucket = AsyncMock(
        side_effect=ClientError({"Error": {"Code": "403"}}, "CreateBucket")
    )

    with pytest.raises(Exception, match="Creation bucket error"):
        await s3_service._ensure_bucket_exists()


@pytest.mark.asyncio
async def test_ensure_bucket_exists_other_error(s3_service):
    """Тест других ошибок при проверке bucket"""
    s3_service.s3_client.head_bucket = AsyncMock(
        side_effect=ClientError({"Error": {"Code": "403"}}, "HeadBucket")
    )

    with pytest.raises(ClientError):
        await s3_service._ensure_bucket_exists()


@pytest.mark.asyncio
async def test_upload_file_success(s3_service, mock_upload_file):
    """Тест успешной загрузки файла"""
    s3_service.s3_client.upload_fileobj = AsyncMock()
    s3_service.__aexit__ = AsyncMock()

    url = await s3_service.upload_file(mock_upload_file, "test-key")

    assert url == "https://s3.example.com/test-prefix-test-bucket/test-key"
    s3_service.s3_client.upload_fileobj.assert_awaited_once_with(
        mock_upload_file.file,
        "test-prefix-test-bucket",
        "test-key",
        ExtraArgs={"ACL": "public-read"}
    )
    s3_service.__aexit__.assert_awaited_once_with(None, None, None)


@pytest.mark.asyncio
async def test_upload_file_error(s3_service, mock_upload_file):
    """Тест ошибки при загрузке файла"""
    s3_service.s3_client.upload_fileobj = AsyncMock(
        side_effect=ClientError({"Error": {"Code": "403"}}, "PutObject")
    )
    s3_service.__aexit__ = AsyncMock()

    with pytest.raises(Exception, match="Uploading file error"):
        await s3_service.upload_file(mock_upload_file, "test-key")

    s3_service.__aexit__.assert_awaited_once_with(None, None, None)


@pytest.mark.asyncio
async def test_delete_file_success(s3_service):
    """Тест успешного удаления файла"""
    s3_service.s3_client.delete_object = AsyncMock()
    s3_service.__aexit__ = AsyncMock()

    await s3_service.delete_file("test-key")

    s3_service.s3_client.delete_object.assert_awaited_once_with(
        Bucket="test-prefix-test-bucket",
        Key="test-key"
    )
    s3_service.__aexit__.assert_awaited_once_with(None, None, None)


@pytest.mark.asyncio
async def test_delete_file_error(s3_service):
    """Тест ошибки при удалении файла"""
    s3_service.s3_client.delete_object = AsyncMock(
        side_effect=ClientError({"Error": {"Code": "404"}}, "DeleteObject")
    )
    s3_service.__aexit__ = AsyncMock()

    with pytest.raises(Exception, match="Deleting file error"):
        await s3_service.delete_file("test-key")

    s3_service.__aexit__.assert_awaited_once_with(None, None, None)


def test_get_file_url(s3_service):
    """Тест получения URL файла"""
    url = s3_service.get_file_url("test-key")
    assert url == "https://s3.example.com/test-prefix-test-bucket/test-key"


@pytest.mark.asyncio
async def test_upload_file_bytes_success(s3_service):
    """Тест успешной загрузки байтов"""
    s3_service.s3_client.put_object = AsyncMock()
    s3_service.__aexit__ = AsyncMock()

    url = await s3_service.upload_file_bytes("test-key", b"test data", "text/plain")

    assert url == "https://s3.example.com/test-prefix-test-bucket/test-key"
    s3_service.s3_client.put_object.assert_awaited_once_with(
        Bucket="test-prefix-test-bucket",
        Key="test-key",
        Body=b"test data",
        ContentType="text/plain",
        ContentDisposition="inline",
        ACL="public-read"
    )
    s3_service.__aexit__.assert_awaited_once_with(None, None, None)


@pytest.mark.asyncio
async def test_upload_file_bytes_without_content_type(s3_service):
    """Тест загрузки байтов без указания content type"""
    s3_service.s3_client.put_object = AsyncMock()
    s3_service.__aexit__ = AsyncMock()

    url = await s3_service.upload_file_bytes("test-key", b"test data")

    assert url == "https://s3.example.com/test-prefix-test-bucket/test-key"
    s3_service.s3_client.put_object.assert_awaited_once_with(
        Bucket="test-prefix-test-bucket",
        Key="test-key",
        Body=b"test data",
        ContentType=None,
        ContentDisposition="inline",
        ACL="public-read"
    )


@pytest.mark.asyncio
async def test_upload_file_bytes_error(s3_service):
    """Тест ошибки при загрузке байтов"""
    s3_service.s3_client.put_object = AsyncMock(
        side_effect=ClientError({"Error": {"Code": "403"}}, "PutObject")
    )
    s3_service.__aexit__ = AsyncMock()

    with pytest.raises(Exception, match="Uploading bytes error"):
        await s3_service.upload_file_bytes("test-key", b"test data")

    s3_service.__aexit__.assert_awaited_once_with(None, None, None)


@pytest.mark.asyncio
async def test_list_files_success(s3_service):
    """Тест успешного получения списка файлов"""
    s3_service.s3_client.list_objects_v2 = AsyncMock(return_value={
        "Contents": [
            {"Key": "file1.txt"},
            {"Key": "file2.txt"},
            {"Key": "folder/file3.txt"}
        ]
    })
    s3_service.__aexit__ = AsyncMock()

    files = await s3_service.list_files("folder/")

    assert files == ["file1.txt", "file2.txt", "folder/file3.txt"]
    s3_service.s3_client.list_objects_v2.assert_awaited_once_with(
        Bucket="test-prefix-test-bucket",
        Prefix="folder/"
    )
    s3_service.__aexit__.assert_awaited_once_with(None, None, None)


@pytest.mark.asyncio
async def test_list_files_empty(s3_service):
    """Тест получения пустого списка файлов"""
    s3_service.s3_client.list_objects_v2 = AsyncMock(return_value={})
    s3_service.__aexit__ = AsyncMock()

    files = await s3_service.list_files()

    assert files == []
    s3_service.s3_client.list_objects_v2.assert_awaited_once_with(
        Bucket="test-prefix-test-bucket",
        Prefix=""
    )


@pytest.mark.asyncio
async def test_list_files_error(s3_service):
    """Тест ошибки при получении списка файлов"""
    s3_service.s3_client.list_objects_v2 = AsyncMock(
        side_effect=ClientError({"Error": {"Code": "403"}}, "ListObjectsV2")
    )
    s3_service.__aexit__ = AsyncMock()

    with pytest.raises(Exception, match="Listing files error"):
        await s3_service.list_files()

    s3_service.__aexit__.assert_awaited_once_with(None, None, None)


@pytest.mark.asyncio
async def test_get_file_bytes_success(s3_service):
    """Тест успешного получения байтов файла"""
    mock_body = AsyncMock()
    mock_body.read = AsyncMock(return_value=b"file content")
    s3_service.s3_client.get_object = AsyncMock(return_value={"Body": mock_body})
    s3_service.__aexit__ = AsyncMock()

    data = await s3_service.get_file_bytes("test-key")

    assert data == b"file content"
    s3_service.s3_client.get_object.assert_awaited_once_with(
        Bucket="test-prefix-test-bucket",
        Key="test-key"
    )
    s3_service.__aexit__.assert_awaited_once_with(None, None, None)


@pytest.mark.asyncio
async def test_get_file_bytes_error(s3_service):
    """Тест ошибки при получении байтов файла"""
    s3_service.s3_client.get_object = AsyncMock(
        side_effect=ClientError({"Error": {"Code": "404"}}, "GetObject")
    )
    s3_service.__aexit__ = AsyncMock()

    with pytest.raises(Exception, match="Error getting file bytes"):
        await s3_service.get_file_bytes("test-key")

    s3_service.__aexit__.assert_awaited_once_with(None, None, None)


@pytest.mark.asyncio
async def test_get_s3_service():
    """Тест функции get_s3_service"""
    from s3_service.main import get_s3_service

    with patch("s3_service.main.S3Service") as mock_s3_service:
        mock_service = AsyncMock()
        mock_s3_service.return_value.__aenter__ = AsyncMock(return_value=mock_service)
        mock_s3_service.return_value.__aexit__ = AsyncMock()

        result = await get_s3_service("test-bucket")

        assert result == mock_service
        mock_s3_service.assert_called_once_with("test-bucket")


@pytest.mark.asyncio
async def test_s3_service_dependency():
    """Тест dependency функции"""
    from s3_service.main import s3_service_dependency

    dependency_func = s3_service_dependency("test-bucket")

    with patch("s3_service.main.S3Service") as mock_s3_service:
        mock_service = AsyncMock()
        mock_s3_service.return_value.__aenter__ = AsyncMock(return_value=mock_service)
        mock_s3_service.return_value.__aexit__ = AsyncMock()

        result = await dependency_func()

        assert result == mock_service
        mock_s3_service.assert_called_once_with("test-bucket")