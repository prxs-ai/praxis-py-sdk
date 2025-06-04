from unittest.mock import AsyncMock

import aiohttp
import pytest
from twitter_follow.main import follow


@pytest.mark.asyncio
async def test_follow_success(mocker):
    mock_response = AsyncMock()
    mock_response.ok = True
    mock_response.json.return_value = {"data": {"following": True}}
    mocker.patch("aiohttp.ClientSession.post", return_value=mock_response)

    result = await follow("token123", "user123", "target456")
    assert result == {"data": {"following": True}}
    aiohttp.ClientSession.post.assert_called_once_with(
        "https://api.x.com/2/users/user123/following",
        headers={
            "Authorization": "Bearer token123",
            "Content-Type": "application/json",
        },
        json={"target_user_id": "target456"},
    )


@pytest.mark.asyncio
async def test_follow_failure(mocker):
    mock_response = AsyncMock()
    mock_response.ok = False
    mock_response.status = 400
    mock_response.text.return_value = "Bad Request"
    mocker.patch("aiohttp.ClientSession.post", return_value=mock_response)

    result = await follow("token123", "user123", "target456")
    assert result == {"error": "Bad Request", "status": 400}
    aiohttp.ClientSession.post.assert_called_once_with(
        "https://api.x.com/2/users/user123/following",
        headers={
            "Authorization": "Bearer token123",
            "Content-Type": "application/json",
        },
        json={"target_user_id": "target456"},
    )
