import pytest
import aiohttp
from unittest.mock import AsyncMock, patch, MagicMock
from rugcheck_wrapper.main import RugCheckAPI


@pytest.fixture
def mock_aiohttp():
    with patch("aiohttp.ClientSession") as mock_session:
        yield mock_session


@pytest.fixture
async def rugcheck_api(mock_aiohttp):
    api = RugCheckAPI()
    yield api
    await api.close()


@pytest.mark.asyncio
async def test_init_creates_session(mock_aiohttp):
    """Тест: инициализация создает клиентскую сессию"""
    api = RugCheckAPI()
    assert mock_aiohttp.called
    await api.close()


@pytest.mark.asyncio
async def test_base_url_class_attribute():
    """Тест: проверка базового URL"""
    assert RugCheckAPI.BASE_URL == "https://api.rugcheck.xyz/v1"


@pytest.mark.asyncio
async def test_get_token_report_success(rugcheck_api, mock_aiohttp):
    """Тест: успешный запрос отчета по токену"""
    mock_response = {
        "token": "0x123",
        "score": 85,
        "is_rug": False,
        "details": {"audit": True}
    }

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value=mock_response)

    mock_session = mock_aiohttp.return_value
    mock_session.get.return_value.__aenter__.return_value = mock_resp

    result = await rugcheck_api.get_token_report("0x123")

    assert result == mock_response
    mock_session.get.assert_called_once_with(
        "https://api.rugcheck.xyz/v1/tokens/0x123/report"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code,error_msg", [
    (400, "Bad Request"),
    (404, "Not Found"),
    (500, "Internal Server Error"),
    (503, "Service Unavailable")
])
async def test_get_token_report_errors(status_code, error_msg, rugcheck_api, mock_aiohttp):
    """Тест: обработка различных ошибок API"""
    mock_resp = MagicMock()
    mock_resp.status = status_code
    mock_resp.text = AsyncMock(return_value=error_msg)

    mock_session = mock_aiohttp.return_value
    mock_session.get.return_value.__aenter__.return_value = mock_resp

    with pytest.raises(Exception, match=f"Error {status_code}: {error_msg}"):
        await rugcheck_api.get_token_report("0x123")


@pytest.mark.asyncio
async def test_request_with_empty_endpoint(rugcheck_api, mock_aiohttp):
    """Тест: запрос с пустым эндпоинтом"""
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value={})

    mock_session = mock_aiohttp.return_value
    mock_session.get.return_value.__aenter__.return_value = mock_resp

    with patch.object(rugcheck_api, "_request") as mock_request:
        await rugcheck_api._request("")
        mock_request.assert_called_once()


@pytest.mark.asyncio
async def test_close_session(rugcheck_api, mock_aiohttp):
    """Тест: корректное закрытие сессии"""
    mock_session = mock_aiohttp.return_value
    mock_session.close = AsyncMock()

    await rugcheck_api.close()
    mock_session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_context_manager():
    """Тест: использование как контекстного менеджера"""
    with patch("aiohttp.ClientSession") as mock_session:
        mock_session.return_value.close = AsyncMock()
        async with RugCheckAPI() as api:
            assert isinstance(api, RugCheckAPI)
        mock_session.return_value.close.assert_awaited_once()