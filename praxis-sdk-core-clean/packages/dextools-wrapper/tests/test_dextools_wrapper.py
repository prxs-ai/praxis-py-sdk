import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiohttp import ClientResponse, ClientSession
from aiolimiter import AsyncLimiter
from dextools_wrapper.main import DextoolsAPIWrapper



@pytest.fixture
def mock_session():
    return MagicMock(spec=ClientSession)


@pytest.fixture
def mock_limiter():
    return MagicMock(spec=AsyncLimiter)


@pytest.fixture
def dextools_wrapper(mock_session, mock_limiter):
    with patch('aiohttp.ClientSession', return_value=mock_session), \
            patch('aiolimiter.AsyncLimiter', return_value=mock_limiter):
        return DextoolsAPIWrapper(
            api_key="test_api_key",
            plan="standard",
            useragent="test-agent",
            requests_per_second=5
        )


@pytest.mark.asyncio
async def test_init(dextools_wrapper, mock_session, mock_limiter):
    assert dextools_wrapper._api_key == "test_api_key"
    assert dextools_wrapper._useragent == "test-agent"
    assert dextools_wrapper.plan == "standard"
    assert dextools_wrapper.url == "https://public-api.dextools.io/standard/v2"
    mock_session.assert_called_once()
    mock_limiter.assert_called_once_with(5, 1)


@pytest.mark.parametrize("plan,expected_url", [
    ("free", "https://public-api.dextools.io/free/v2"),
    ("trial", "https://public-api.dextools.io/trial/v2"),
    ("standard", "https://public-api.dextools.io/standard/v2"),
    ("advanced", "https://public-api.dextools.io/advanced/v2"),
    ("pro", "https://public-api.dextools.io/pro/v2"),
    ("partner", "https://api.dextools.io/v2"),
])
def test_set_plan_success(dextools_wrapper, plan, expected_url):
    dextools_wrapper.set_plan(plan)
    assert dextools_wrapper.plan == plan
    assert dextools_wrapper.url == expected_url
    assert dextools_wrapper._headers == {
        "X-API-Key": "test_api_key",
        "Accept": "application/json",
        "User-Agent": "test-agent",
    }


def test_set_plan_invalid():
    with patch('aiohttp.ClientSession'), patch('aiolimiter.AsyncLimiter'):
        wrapper = DextoolsAPIWrapper(api_key="test", plan="standard")
        with pytest.raises(ValueError, match="Plan not found"):
            wrapper.set_plan("invalid_plan")


@pytest.mark.asyncio
async def test_context_manager():
    mock_session = MagicMock(spec=ClientSession)
    with patch('aiohttp.ClientSession', return_value=mock_session), \
            patch('aiolimiter.AsyncLimiter'):
        async with DextoolsAPIWrapper("test", "standard") as wrapper:
            assert isinstance(wrapper, DextoolsAPIWrapper)
        mock_session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_close(dextools_wrapper, mock_session):
    await dextools_wrapper.close()
    mock_session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_request_success(dextools_wrapper, mock_session, mock_limiter):
    mock_response = MagicMock(spec=ClientResponse)
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"data": "test"})
    mock_session.get.return_value.__aenter__.return_value = mock_response

    result = await dextools_wrapper._request("/test", {"param": "value"})

    assert result == {"data": "test"}
    mock_limiter.acquire.assert_awaited_once()
    mock_session.get.assert_called_once_with(
        "https://public-api.dextools.io/standard/v2/test",
        headers=dextools_wrapper._headers,
        params={"param": "value"}
    )


@pytest.mark.asyncio
async def test_request_rate_limited(dextools_wrapper, mock_limiter):
    mock_limiter.acquire.side_effect = [None, None]
    mock_response = MagicMock(spec=ClientResponse)
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={})
    with patch.object(dextools_wrapper, '_session') as mock_session:
        mock_session.get.return_value.__aenter__.return_value = mock_response
        await dextools_wrapper._request("/test")
        mock_limiter.acquire.assert_awaited()


@pytest.mark.asyncio
async def test_request_403_error(dextools_wrapper, mock_session):
    mock_response = MagicMock(spec=ClientResponse)
    mock_response.status = 403
    mock_response.text = AsyncMock(return_value="Forbidden")
    mock_session.get.return_value.__aenter__.return_value = mock_response

    with pytest.raises(Exception, match="Access denied"):
        await dextools_wrapper._request("/test")


@pytest.mark.asyncio
async def test_get_blockchain(dextools_wrapper):
    with patch.object(dextools_wrapper, '_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"chain": "data"}
        result = await dextools_wrapper.get_blockchain("solana")
        assert result == {"chain": "data"}
        mock_request.assert_awaited_once_with("/blockchain/solana")


@pytest.mark.asyncio
async def test_get_blockchains(dextools_wrapper):
    with patch.object(dextools_wrapper, '_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"chains": []}
        result = await dextools_wrapper.get_blockchains(
            order="desc",
            sort="volume",
            page=2,
            pageSize=50
        )
        assert result == {"chains": []}
        mock_request.assert_awaited_once_with(
            "/blockchain",
            params={"order": "desc", "sort": "volume", "page": 2, "pageSize": 50}
        )


@pytest.mark.asyncio
async def test_get_pool_by_address(dextools_wrapper):
    with patch.object(dextools_wrapper, '_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"pool": "data"}
        result = await dextools_wrapper.get_pool_by_address("solana", "addr123")
        assert result == {"pool": "data"}
        mock_request.assert_awaited_once_with("/pool/solana/addr123")


@pytest.mark.asyncio
async def test_get_pools(dextools_wrapper):
    with patch.object(dextools_wrapper, '_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"pools": []}
        result = await dextools_wrapper.get_pools(
            chain="solana",
            from_="2023-01-01",
            to="2023-01-02",
            order="desc",
            sort="volume",
            page=1,
            pageSize=10
        )
        assert result == {"pools": []}
        mock_request.assert_awaited_once_with(
            "/pool/solana",
            params={
                "from": "2023-01-01",
                "to": "2023-01-02",
                "order": "desc",
                "sort": "volume",
                "page": 1,
                "pageSize": 10
            }
        )
