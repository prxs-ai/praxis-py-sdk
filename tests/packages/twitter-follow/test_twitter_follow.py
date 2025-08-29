import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from twitter_follow.main import follow


@pytest.mark.asyncio
async def test_follow_success():
    mock_response = AsyncMock()
    mock_response.ok = True
    mock_response.status = 200
    mock_response.json.return_value = {"data": {"following": True}}

    with patch("aiohttp.ClientSession") as mock_session:
        mock_session.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

        result = await follow(
            token="test_token",
            user_id="user123",
            target_user_id="target_user456"
        )

        assert result == {"data": {"following": True}}
        mock_session.return_value.__aenter__.return_value.post.assert_awaited_once_with(
            "https://api.x.com/2/users/user123/following",
            headers={
                "Authorization": "Bearer test_token",
                "Content-Type": "application/json"
            },
            json={"target_user_id": "target_user456"}
        )


@pytest.mark.asyncio
async def test_follow_failure():
    mock_response = AsyncMock()
    mock_response.ok = False
    mock_response.status = 403
    mock_response.text.return_value = "Forbidden"

    with patch("aiohttp.ClientSession") as mock_session:
        mock_session.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

        result = await follow(
            token="test_token",
            user_id="user123",
            target_user_id="target_user456"
        )

        assert result == {"error": "Forbidden", "status": 403}


@pytest.mark.asyncio
async def test_follow_network_error():
    with patch("aiohttp.ClientSession") as mock_session:
        mock_session.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=aiohttp.ClientError("Network error")
        )

        with pytest.raises(aiohttp.ClientError, match="Network error"):
            await follow(
                token="test_token",
                user_id="user123",
                target_user_id="target_user456"
            )


@pytest.mark.asyncio
async def test_follow_empty_user_id():
    with pytest.raises(ValueError, match="User ID cannot be empty"):
        await follow(
            token="test_token",
            user_id="",
            target_user_id="target_user456"
        )


@pytest.mark.asyncio
async def test_follow_empty_target_user_id():
    with pytest.raises(ValueError, match="Target user ID cannot be empty"):
        await follow(
            token="test_token",
            user_id="user123",
            target_user_id=""
        )


@pytest.mark.asyncio
async def test_follow_empty_token():
    with pytest.raises(ValueError, match="Token cannot be empty"):
        await follow(
            token="",
            user_id="user123",
            target_user_id="target_user456"
        )


@pytest.mark.asyncio
async def test_follow_json_decode_error():
    mock_response = AsyncMock()
    mock_response.ok = True
    mock_response.status = 200
    mock_response.json.side_effect = ValueError("Invalid JSON")

    with patch("aiohttp.ClientSession") as mock_session:
        mock_session.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

        with pytest.raises(ValueError, match="Invalid JSON"):
            await follow(
                token="test_token",
                user_id="user123",
                target_user_id="target_user456"
            )


@pytest.mark.asyncio
async def test_follow_timeout_error():
    with patch("aiohttp.ClientSession") as mock_session:
        mock_session.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=asyncio.TimeoutError("Request timed out")
        )

        with pytest.raises(asyncio.TimeoutError, match="Request timed out"):
            await follow(
                token="test_token",
                user_id="user123",
                target_user_id="target_user456"
            )
