import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiohttp import ClientResponse, ClientSession
from collections import defaultdict
from dexscreener_wrapper.main import DexScreenerAPI
import time
import asyncio


@pytest.fixture
def mock_session():
    return MagicMock(spec=ClientSession)


@pytest.fixture
def dex_screener(mock_session):
    with patch('aiohttp.ClientSession', return_value=mock_session):
        return DexScreenerAPI()


@pytest.fixture
def mock_response():
    response = MagicMock(spec=ClientResponse)
    response.status = 200
    response.json = AsyncMock(return_value={"data": "test"})
    return response


@pytest.mark.asyncio
async def test_check_rate_limit_no_limit(dex_screener):
    # Для эндпоинта без лимита
    await dex_screener._check_rate_limit("unknown_endpoint")
    assert "unknown_endpoint" not in dex_screener.request_timestamps


@pytest.mark.asyncio
async def test_check_rate_limit_within_limit(dex_screener):
    endpoint = "GET /token-profiles/latest/v1"
    dex_screener.request_timestamps[endpoint] = [time.time() - 30] * 50  # 50 запросов за 30 сек
    await dex_screener._check_rate_limit(endpoint)
    assert len(dex_screener.request_timestamps[endpoint]) == 51


@pytest.mark.asyncio
async def test_check_rate_limit_exceeded(dex_screener, capsys):
    endpoint = "GET /token-profiles/latest/v1"
    dex_screener.request_timestamps[endpoint] = [time.time() - 30] * 60  # 60 запросов за 30 сек

    with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
        await dex_screener._check_rate_limit(endpoint)
        mock_sleep.assert_awaited_once()
        assert "Rate limit exceeded" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_request_success(dex_screener, mock_session, mock_response):
    endpoint = "/test_endpoint"
    params = {"param": "value"}
    mock_session.get.return_value.__aenter__.return_value = mock_response

    result = await dex_screener._request(endpoint, params)

    assert result == {"data": "test"}
    mock_session.get.assert_called_once_with(
        "https://api.dexscreener.com/test_endpoint",
        params=params
    )


@pytest.mark.asyncio
async def test_request_error(dex_screener, mock_session):
    endpoint = "/test_endpoint"
    mock_response = MagicMock(spec=ClientResponse)
    mock_response.status = 400
    mock_response.text = AsyncMock(return_value="Bad Request")
    mock_session.get.return_value.__aenter__.return_value = mock_response

    with pytest.raises(Exception) as exc_info:
        await dex_screener._request(endpoint)

    assert "Error 400" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_latest_token_profiles(dex_screener):
    with patch.object(dex_screener, '_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"profiles": []}
        result = await dex_screener.get_latest_token_profiles()
        assert result == {"profiles": []}
        mock_request.assert_awaited_once_with("/token-profiles/latest/v1")


@pytest.mark.asyncio
async def test_get_pairs_data_by_pool_address(dex_screener):
    with patch.object(dex_screener, '_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"pair": "data"}
        result = await dex_screener.get_pairs_data_by_pool_address("solana", "address123")
        assert result == {"pair": "data"}
        mock_request.assert_awaited_once_with("/latest/dex/pairs/solana/address123")


@pytest.mark.asyncio
async def test_get_token_data_by_address(dex_screener):
    with patch.object(dex_screener, '_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"token": "data"}
        result = await dex_screener.get_token_data_by_address("ether", "token123")
        assert result == {"token": "data"}
        mock_request.assert_awaited_once_with("/tokens/v1/ether/token123")


@pytest.mark.asyncio
async def test_close(dex_screener, mock_session):
    await dex_screener.close()
    mock_session.close.assert_awaited_once()


def test_rate_limits_defined():
    assert DexScreenerAPI.RATE_LIMITS == {
        "GET /token-profiles/latest/v1": (60, 60),
        "GET /latest/dex/pairs": (300, 60),
    }


@pytest.mark.asyncio
async def test_rate_limit_cleanup(dex_screener):
    endpoint = "GET /token-profiles/latest/v1"
    now = time.time()
    dex_screener.request_timestamps[endpoint] = [now - 120, now - 30, now - 10]

    await dex_screener._check_rate_limit(endpoint)

    assert len(dex_screener.request_timestamps[endpoint]) == 3  # 1 удалился, 1 добавился
