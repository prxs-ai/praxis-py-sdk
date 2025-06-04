from unittest.mock import AsyncMock

import pytest
from dexscreener_api import DexScreenerAPI


@pytest.fixture
async def dex_screener_api():
    api = DexScreenerAPI()
    yield api
    await api.close()


@pytest.mark.asyncio
async def test_check_rate_limit_within_limit(dex_screener_api, mocker):
    endpoint = "GET /token-profiles/latest/v1"
    mocker.patch("time.time", return_value=1000.0)
    dex_screener_api.request_timestamps[endpoint] = [
        1000.0 - 30
    ] * 59  # 59 requests within window

    await dex_screener_api._check_rate_limit(endpoint)
    assert len(dex_screener_api.request_timestamps[endpoint]) == 60
    assert dex_screener_api.request_timestamps[endpoint][-1] == 1000.0


@pytest.mark.asyncio
async def test_check_rate_limit_exceeded(dex_screener_api, mocker):
    endpoint = "GET /token-profiles/latest/v1"
    mocker.patch("time.time", side_effect=[1000.0, 1000.0, 1005.0])
    mock_sleep = mocker.patch("asyncio.sleep", new=AsyncMock())
    dex_screener_api.request_timestamps[endpoint] = [1000.0 - 30] * 60  # 60 requests

    await dex_screener_api._check_rate_limit(endpoint)
    mock_sleep.assert_called_once_with(30.0)
    assert len(dex_screener_api.request_timestamps[endpoint]) == 1
    assert dex_screener_api.request_timestamps[endpoint][0] == 1005.0


@pytest.mark.asyncio
async def test_check_rate_limit_no_limit(dex_screener_api, mocker):
    endpoint = "GET /unknown"
    mocker.patch("time.time", return_value=1000.0)
    await dex_screener_api._check_rate_limit(endpoint)
    assert endpoint not in dex_screener_api.request_timestamps


@pytest.mark.asyncio
async def test_request_success(dex_screener_api, mocker):
    endpoint = "token-profiles/latest/v1"
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {"data": "test"}
    mocker.patch.object(dex_screener_api.session, "get", return_value=mock_response)
    mocker.patch("asyncio.sleep", new=AsyncMock())

    result = await dex_screener_api._request(endpoint, params={"key": "value"})
    assert result == {"data": "test"}
    dex_screener_api.session.get.assert_called_once_with(
        f"{dex_screener_api.BASE_URL}{endpoint}", params={"key": "value"}
    )


@pytest.mark.asyncio
async def test_request_failure(dex_screener_api, mocker):
    endpoint = "token-profiles/latest/v1"
    mock_response = AsyncMock()
    mock_response.status = 400
    mock_response.text.return_value = "Bad Request"
    mocker.patch.object(dex_screener_api.session, "get", return_value=mock_response)
    mocker.patch("asyncio.sleep", new=AsyncMock())

    with pytest.raises(Exception, match="Error 400: Bad Request"):
        await dex_screener_api._request(endpoint)


@pytest.mark.asyncio
async def test_get_latest_token_profiles(dex_screener_api, mocker):
    mock_response = {"profiles": ["profile1", "profile2"]}
    mocker.patch.object(
        dex_screener_api, "_request", AsyncMock(return_value=mock_response)
    )

    result = await dex_screener_api.get_latest_token_profiles()
    assert result == mock_response
    dex_screener_api._request.assert_called_once_with("/token-profiles/latest/v1")


@pytest.mark.asyncio
async def test_get_pairs_data_by_pool_address(dex_screener_api, mocker):
    mock_response = {"pair": "data"}
    mocker.patch.object(
        dex_screener_api, "_request", AsyncMock(return_value=mock_response)
    )

    result = await dex_screener_api.get_pairs_data_by_pool_address(
        "solana", "6xzcGi7rMd12UPD5PJSMnkTgquBZFYhhMz9D5iHgzB1w"
    )
    assert result == mock_response
    dex_screener_api._request.assert_called_once_with(
        "/latest/dex/pairs/solana/6xzcGi7rMd12UPD5PJSMnkTgquBZFYhhMz9D5iHgzB1w"
    )


@pytest.mark.asyncio
async def test_get_token_data_by_address(dex_screener_api, mocker):
    mock_response = {"token": "data"}
    mocker.patch.object(
        dex_screener_api, "_request", AsyncMock(return_value=mock_response)
    )

    result = await dex_screener_api.get_token_data_by_address(
        "ether", "6xzcGi7rMd12UPD5PJSMnkTgquBZFYhhMz9D5iHgzB1w"
    )
    assert result == mock_response
    dex_screener_api._request.assert_called_once_with(
        "/tokens/v1/ether/6xzcGi7rMd12UPD5PJSMnkTgquBZFYhhMz9D5iHgzB1w"
    )


@pytest.mark.asyncio
async def test_close_session(dex_screener_api, mocker):
    mock_close = mocker.patch.object(dex_screener_api.session, "close", new=AsyncMock())
    await dex_screener_api.close()
    mock_close.assert_called_once()
