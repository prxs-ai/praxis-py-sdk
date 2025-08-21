import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from twitter_follow_unfollow_get_likes_on_post.main import get_likes_on_post
import aiohttp


@pytest.fixture
def mock_logger():
    with patch("twitter_follow_unfollow_get_likes_on_post.main.logger") as mock:
        yield mock


@pytest.mark.asyncio
async def test_get_likes_on_post_success(mock_logger):
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.__aenter__.return_value = mock_response
    mock_response.json.return_value = {"data": [{"id": "123", "name": "test_user"}]}

    with patch("aiohttp.ClientSession") as mock_session:
        mock_session.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

        result = await get_likes_on_post(
            access_token="test_token",
            tweet_id="tweet123"
        )

        assert result == {"data": [{"id": "123", "name": "test_user"}]}
        mock_session.return_value.__aenter__.return_value.get.assert_awaited_once_with(
            "https://api.x.com/2/tweets/tweet123/liking_users",
            headers={"Authorization": "Bearer test_token"}
        )
        mock_logger.info.assert_any_call("Getting user notifications")
        mock_logger.info.assert_any_call("Notifications received: {'data': [{'id': '123', 'name': 'test_user'}]}")


@pytest.mark.asyncio
async def test_get_likes_on_post_failure(mock_logger):
    mock_response = AsyncMock()
    mock_response.status = 404
    mock_response.__aenter__.return_value = mock_response
    mock_response.text.return_value = "Not Found"

    with patch("aiohttp.ClientSession") as mock_session:
        mock_session.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

        result = await get_likes_on_post(
            access_token="test_token",
            tweet_id="tweet123"
        )

        assert result is None
        mock_logger.info.assert_any_call("Getting user notifications")
        mock_logger.info.assert_any_call("Notifications not received: Not Found")


@pytest.mark.asyncio
async def test_get_likes_on_post_network_error(mock_logger):
    with patch("aiohttp.ClientSession") as mock_session:
        mock_session.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=aiohttp.ClientError("Network error")
        )

        result = await get_likes_on_post(
            access_token="test_token",
            tweet_id="tweet123"
        )

        assert result is None
        mock_logger.info.assert_called_once_with("Getting user notifications")


@pytest.mark.asyncio
async def test_get_likes_on_post_empty_token():
    with pytest.raises(ValueError, match="Access token cannot be empty"):
        await get_likes_on_post(
            access_token="",
            tweet_id="tweet123"
        )


@pytest.mark.asyncio
async def test_get_likes_on_post_empty_tweet_id():
    with pytest.raises(ValueError, match="Tweet ID cannot be empty"):
        await get_likes_on_post(
            access_token="test_token",
            tweet_id=""
        )


@pytest.mark.asyncio
async def test_get_likes_on_post_json_error(mock_logger):
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.__aenter__.return_value = mock_response
    mock_response.json.side_effect = ValueError("Invalid JSON")

    with patch("aiohttp.ClientSession") as mock_session:
        mock_session.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

        result = await get_likes_on_post(
            access_token="test_token",
            tweet_id="tweet123"
        )

        assert result is None
        mock_logger.info.assert_any_call("Getting user notifications")


@pytest.mark.asyncio
async def test_get_likes_on_post_timeout_error(mock_logger):
    with patch("aiohttp.ClientSession") as mock_session:
        mock_session.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=asyncio.TimeoutError("Request timed out")
        )

        result = await get_likes_on_post(
            access_token="test_token",
            tweet_id="tweet123"
        )

        assert result is None
        mock_logger.info.assert_called_once_with("Getting user notifications")


@pytest.mark.asyncio
async def test_get_likes_on_post_500_error(mock_logger):
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_response.__aenter__.return_value = mock_response
    mock_response.text.return_value = "Internal Server Error"

    with patch("aiohttp.ClientSession") as mock_session:
        mock_session.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

        result = await get_likes_on_post(
            access_token="test_token",
            tweet_id="tweet123"
        )

        assert result is None
        mock_logger.info.assert_any_call("Notifications not received: Internal Server Error")
