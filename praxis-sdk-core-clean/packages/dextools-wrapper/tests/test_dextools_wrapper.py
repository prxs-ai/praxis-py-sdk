from unittest.mock import AsyncMock

import aiohttp
import pytest
from dexscreener_api import DextoolsAPIWrapper


@pytest.fixture
async def dextools_api():
    api = DextoolsAPIWrapper(api_key="test_key", plan="free", requests_per_second=1)
    yield api
    await api.close()


@pytest.mark.asyncio
async def test_set_plan_valid(dextools_api):
    dextools_api.set_plan("standard")
    assert dextools_api.plan == "standard"
    assert dextools_api.url == "https://public-api.dextools.io/standard/v2"
    assert dextools_api._headers == {
        "X-API-Key": "test_key",
        "Accept": "application/json",
        "User-Agent": "API-Wrapper/0.3",
    }


@pytest.mark.asyncio
async def test_set_plan_partner(dextools_api):
    dextools_api.set_plan("partner")
    assert dextools_api.plan == "partner"
    assert dextools_api.url == "https://api.dextools.io/v2"


@pytest.mark.asyncio
async def test_set_plan_invalid(dextools_api):
    with pytest.raises(ValueError, match="Plan not found"):
        dextools_api.set_plan("invalid")


@pytest.mark.asyncio
async def test_context_manager(dextools_api, mocker):
    mock_close = mocker.patch.object(dextools_api, "close", new=AsyncMock())
    async with DextoolsAPIWrapper(api_key="test_key", plan="free") as api:
        assert api.plan == "free"
    mock_close.assert_called_once()


@pytest.mark.asyncio
async def test_request_success(dextools_api, mocker):
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {"data": "test"}
    mocker.patch.object(dextools_api._session, "get", return_value=mock_response)
    mocker.patch("aiolimiter.AsyncLimiter.__aenter__", new=AsyncMock())

    result = await dextools_api._request("/test", params={"key": "value"})
    assert result == {"data": "test"}
    dextools_api._session.get.assert_called_once_with(
        "https://public-api.dextools.io/free/v2/test",
        headers=dextools_api._headers,
        params={"key": "value"},
    )


@pytest.mark.asyncio
async def test_request_403_error(dextools_api, mocker):
    mock_response = AsyncMock()
    mock_response.status = 403
    mock_response.raise_for_status.side_effect = aiohttp.ClientResponseError(
        status=403, request_info=None, history=None, message="Forbidden"
    )
    mocker.patch.object(dextools_api._session, "get", return_value=mock_response)
    mocker.patch("aiolimiter.AsyncLimiter.__aenter__", new=AsyncMock())

    with pytest.raises(
        Exception, match=r"Access denied \(403\). Check your API key or request limits."
    ):
        await dextools_api._request("/test")


@pytest.mark.asyncio
async def test_get_blockchain(dextools_api, mocker):
    mock_response = {"chain": "solana"}
    mocker.patch.object(dextools_api, "_request", AsyncMock(return_value=mock_response))

    result = await dextools_api.get_blockchain("solana")
    assert result == mock_response
    dextools_api._request.assert_called_once_with("/blockchain/solana")


@pytest.mark.asyncio
async def test_get_blockchains(dextools_api, mocker):
    mock_response = {"blockchains": ["solana", "ether"]}
    mocker.patch.object(dextools_api, "_request", AsyncMock(return_value=mock_response))

    result = await dextools_api.get_blockchains(
        order="desc", sort="id", page=1, pageSize=10
    )
    assert result == mock_response
    dextools_api._request.assert_called_once_with(
        "/blockchain", params={"order": "desc", "sort": "id", "page": 1, "pageSize": 10}
    )


@pytest.mark.asyncio
async def test_get_pool_by_address(dextools_api, mocker):
    mock_response = {"pool": "data"}
    mocker.patch.object(dextools_api, "_request", AsyncMock(return_value=mock_response))

    result = await dextools_api.get_pool_by_address(
        "solana", "8f94e3kYk9ZPuEPT5Zgo9tiVJvwaj8zUzbPFPqt2MKK2"
    )
    assert result == mock_response
    dextools_api._request.assert_called_once_with(
        "/pool/solana/8f94e3kYk9ZPuEPT5Zgo9tiVJvwaj8zUzbPFPqt2MKK2"
    )


@pytest.mark.asyncio
async def test_get_pools(dextools_api, mocker):
    mock_response = {"pools": ["pool1", "pool2"]}
    mocker.patch.object(dextools_api, "_request", AsyncMock(return_value=mock_response))

    result = await dextools_api.get_pools(
        chain="solana",
        from_="2023-11-14",
        to="2023-11-15",
        order="desc",
        sort="volume",
        page=1,
        pageSize=10,
    )
    assert result == mock_response
    dextools_api._request.assert_called_once_with(
        "/pool/solana",
        params={
            "from": "2023-11-14",
            "to": "2023-11-15",
            "order": "desc",
            "sort": "volume",
            "page": 1,
            "pageSize": 10,
        },
    )


@pytest.mark.asyncio
async def test_get_pools_partial_params(dextools_api, mocker):
    mock_response = {"pools": ["pool1"]}
    mocker.patch.object(dextools_api, "_request", AsyncMock(return_value=mock_response))

    result = await dextools_api.get_pools(
        chain="solana", from_="2023-11-14", to="2023-11-15"
    )
    assert result == mock_response
    dextools_api._request.assert_called_once_with(
        "/pool/solana",
        params={
            "from": "2023-11-14",
            "to": "2023-11-15",
            "order": "asc",
            "sort": "creationTime",
        },
    )
