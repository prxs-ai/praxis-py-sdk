import pytest
from unittest.mock import AsyncMock, patch
import time
from datetime import datetime
from redis_client.main import Post
from redis_utils.main import ensure_delay_between_posts, decode_redis
from loguru import logger


@pytest.fixture
def mock_redis():
    return Mock()


@pytest.fixture
def username():
    return "testuser"


@pytest.mark.asyncio
async def test_ensure_delay_between_posts_no_delay(mocker, username):
    mocker.patch("redis_client.get_redis_db")  # Mock Redis to avoid actual calls
    mocker.patch("random.randint", return_value=300)  # 5 minutes
    mocker.patch("time.time", return_value=1672574400 + 1000)  # Some time after past_date
    mocker.patch("asyncio.sleep", new=AsyncMock())
    mocker.patch.object(logger, "info")

    await ensure_delay_between_posts(username)
    logger.info.assert_any_call(f"ensure_delay_between_posts {username=} len(posts)=2")
    logger.info.assert_any_call(f"ensure_delay_between_posts {username=} time_since_last_post=1000.0")
    asyncio.sleep.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_delay_between_posts_with_delay(mocker, username):
    past_date = datetime(2023, 1, 1, 12, 0)
    mocker.patch("redis_client.get_redis_db")  # Mock Redis
    mocker.patch("time.time", return_value=past_date.timestamp() + 100)
    mocker.patch("random.randint", return_value=300)  # 5 minutes
    mock_sleep = mocker.patch("asyncio.sleep", new=AsyncMock())
    mocker.patch.object(logger, "info")

    await ensure_delay_between_posts(username)
    logger.info.assert_any_call(f"ensure_delay_between_posts {username=} len(posts)=2")
    logger.info.assert_any_call(f"ensure_delay_between_posts {username=} time_since_last_post=100.0")
    logger.info.assert_any_call(f"Waiting: {username=} wait_time=200.0")
    mock_sleep.assert_called_once_with(200.0)


@pytest.mark.asyncio
async def test_ensure_delay_between_posts_custom_delay(mocker, username):
    past_date = datetime(2023, 1, 1, 12, 0)
    mocker.patch("redis_client.get_redis_db")  # Mock Redis
    mocker.patch("time.time", return_value=past_date.timestamp() + 50)
    mock_sleep = mocker.patch("asyncio.sleep", new=AsyncMock())
    mocker.patch.object(logger, "info")

    await ensure_delay_between_posts(username, delay=100)
    logger.info.assert_any_call(f"ensure_delay_between_posts {username=} len(posts)=2")
    logger.info.assert_any_call(f"ensure_delay_between_posts {username=} time_since_last_post=50.0")
    logger.info.assert_any_call(f"Waiting: {username=} wait_time=50.0")
    mock_sleep.assert_called_once_with(50.0)


@pytest.mark.asyncio
async def test_decode_redis_list():
    src = [b"item1", b"item2"]
    result = decode_redis(src)
    assert result == ["item1", "item2"]


@pytest.mark.asyncio
async def test_decode_redis_dict():
    src = {b"key1": b"value1", b"key2": [b"item1", b"item2"]}
    result = decode_redis(src)
    assert result == {"key1": "value1", "key2": ["item1", "item2"]}


@pytest.mark.asyncio
async def test_decode_redis_bytes():
    src = b"test"
    result = decode_redis(src)
    assert result == "test"


@pytest.mark.asyncio
async def test_decode_redis_invalid_type():
    src = 123
    with pytest.raises(Exception, match="type not handled: int"):
        decode_redis(src)
