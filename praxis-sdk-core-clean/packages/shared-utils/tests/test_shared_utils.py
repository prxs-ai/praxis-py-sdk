import pytest
import aiohttp
from unittest.mock import AsyncMock, patch, MagicMock
from shared_utils.enums import AppPlatformEnum
from shared_utils.http_client import HttpClient
from loguru import logger


@pytest.fixture(scope="session", autouse=True)
def setup_mocks():
    """
    Настройка глобальных моков для всей сессии тестирования.
    Этот фикстура запускается один раз в начале тестовой сессии
    и обеспечивает, чтобы моки для настроек OpenAI были применены
    до того, как какие-либо модули попытаются их загрузить.
    """

    mock_settings = MagicMock()
    mock_settings.OPENAI_API_KEY = "test-api-key-12345"
    mock_settings.OPEN_AI_MODEL = "gpt-4"
    mock_settings.OPENAI_EMBEDDING_MODEL = "text-embedding-ada-002"

    mock_config_module = MagicMock()
    mock_config_module.get_settings.return_value = mock_settings

    with patch.dict('sys.modules', {
        'send_openai_request.config': mock_config_module
    }):
        yield


@pytest.fixture(autouse=True)
def mock_openai_client():
    """
    Мокаем OpenAI клиент для каждого теста.
    Гарантирует, что вызовы к OpenAI API перехватываются.
    """
    with patch("openai.AsyncOpenAI") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        with patch("send_openai_request.main.client", mock_client):
            yield mock_client


def test_app_platform_enum_values(mock_openai_client, setup_mocks):
    assert AppPlatformEnum.ANDROID == "android"
    assert AppPlatformEnum.IOS == "ios"
    assert AppPlatformEnum.WP == "wp"
    assert AppPlatformEnum.BB == "bb"
    assert AppPlatformEnum.DESKTOP == "desktop"
    assert AppPlatformEnum.WEB == "web"
    assert AppPlatformEnum.UBP == "ubp"
    assert AppPlatformEnum.OTHER == "other"


def test_app_platform_enum_is_string(mock_openai_client, setup_mocks):
    for platform in AppPlatformEnum:
        assert isinstance(platform.value, str)


def test_app_platform_enum_members(mock_openai_client, setup_mocks):
    expected_members = {"ANDROID", "IOS", "WP", "BB", "DESKTOP", "WEB", "UBP", "OTHER"}
    actual_members = {member.name for member in AppPlatformEnum}
    assert actual_members == expected_members


@pytest.mark.asyncio
async def test_http_client_post_success(mock_openai_client, setup_mocks):
    base_url = "https://api.example.com"
    endpoint = "/test"
    data = {"key": "value"}
    headers = {"Authorization": "Bearer token"}

    with patch("aiohttp.ClientSession.post", new=AsyncMock()) as mock_post:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.raise_for_status = lambda: None
        mock_post.return_value.__aenter__.return_value = mock_response

        client = HttpClient(base_url)
        response = await client.post(endpoint, data, headers)

        mock_post.assert_called_with(f"{base_url}{endpoint}", data=data, headers=headers)
        assert response.status == 200


@pytest.mark.asyncio
async def test_http_client_get_success(mock_openai_client, setup_mocks):
    base_url = "https://api.example.com"
    endpoint = "/test"
    headers = {"Authorization": "Bearer token"}

    with patch("aiohttp.ClientSession.get", new=AsyncMock()) as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.raise_for_status = lambda: None
        mock_get.return_value.__aenter__.return_value = mock_response

        client = HttpClient(base_url)
        response = await client.get(endpoint, headers)

        mock_get.assert_called_with(f"{base_url}{endpoint}", headers=headers)
        assert response.status == 200


@pytest.mark.asyncio
async def test_http_client_post_raises_error(mock_openai_client, setup_mocks):
    base_url = "https://api.example.com"
    endpoint = "/test"
    data = {"key": "value"}

    with patch("aiohttp.ClientSession.post", new=AsyncMock()) as mock_post:
        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.raise_for_status.side_effect = aiohttp.ClientResponseError(
            status=400, message="Bad Request", request_info=None, history=None
        )
        mock_post.return_value.__aenter__.return_value = mock_response

        client = HttpClient(base_url)
        with pytest.raises(aiohttp.ClientResponseError):
            await client.post(endpoint, data)


@pytest.mark.asyncio
async def test_format_text_success_short_text(mock_openai_client, setup_mocks):
    from shared_utils.utils import format_text, add_blank_lines
    input_text = "Short text"
    with patch("shared_utils.utils.send_openai_request", new=AsyncMock()) as mock_openai_request:
        with patch("shared_utils.utils.add_blank_lines", new=AsyncMock()) as mock_add_blank_lines:
            mock_add_blank_lines.return_value = input_text
            result = await format_text(input_text)
            assert result == input_text
            mock_add_blank_lines.assert_called_once_with(input_text)
            mock_openai_request.assert_not_called()


@pytest.mark.asyncio
async def test_format_text_long_text_success(mock_openai_client, setup_mocks):
    from shared_utils.utils import format_text, add_blank_lines
    input_text = "This is a very long text " * 20
    shortened_text = "This is a short text"

    with patch("shared_utils.utils.send_openai_request", new=AsyncMock()) as mock_openai:
        with patch("shared_utils.utils.add_blank_lines", new=AsyncMock()) as mock_add_blank_lines:
            mock_openai.return_value = shortened_text
            mock_add_blank_lines.side_effect = [input_text, shortened_text]

            result = await format_text(input_text)

            assert result == shortened_text
            mock_openai.assert_called_once()
            assert mock_add_blank_lines.call_count == 2


@pytest.mark.asyncio
async def test_format_text_too_long_error(mock_openai_client, setup_mocks):
    from shared_utils.utils import format_text, add_blank_lines
    input_text = "This is a very long text " * 20

    with patch("shared_utils.utils.send_openai_request", new=AsyncMock()) as mock_openai:
        with patch("shared_utils.utils.add_blank_lines", new=AsyncMock()) as mock_add_blank_lines:
            mock_openai.return_value = input_text + " still too long"
            mock_add_blank_lines.return_value = input_text + " still too long"

            with pytest.raises(ValueError, match="Generated text is too long"):
                await format_text(input_text)

            assert mock_openai.call_count == 20


@pytest.mark.asyncio
async def test_add_blank_lines(mock_openai_client, setup_mocks):
    from shared_utils.utils import format_text, add_blank_lines
    input_text = "Sentence one. Sentence two. Sentence three."
    expected_output = "Sentence one.\n\nSentence two.\n\nSentence three."

    with patch("shared_utils.utils.send_openai_request", new=AsyncMock()) as mock_openai:
        mock_openai.return_value = expected_output
        result = await add_blank_lines(input_text)

        assert result == expected_output
        mock_openai.assert_called_once()
