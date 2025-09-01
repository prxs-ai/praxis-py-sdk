import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

with patch("redis_client.config.Settings") as mock_settings:
    mock_settings.return_value = MagicMock(
        REDIS_HOST="mock_host",
        REDIS_PORT=6379,
        REDIS_DB=0,
    )
    with patch("redis_client.main.RedisDB"):
        from redis_utils.main import ensure_delay_between_posts, decode_redis


class Post:
    def __init__(self, id, text, sender_username, timestamp, is_news_summary_tweet=False):
        self.id = id
        self.text = text
        self.sender_username = sender_username
        self.timestamp = timestamp
        self.is_news_summary_tweet = is_news_summary_tweet


@pytest.fixture
def mock_redis():
    with patch("redis_utils.main.db") as mock_db:
        yield mock_db


@pytest.fixture
def mock_time():
    with patch("time.time") as mock_time:
        yield mock_time


@pytest.mark.asyncio
async def test_ensure_delay_no_posts(mock_redis):
    """Тест: если постов нет, функция не должна ждать."""
    mock_redis.get_posts_by_username.return_value = []

    await ensure_delay_between_posts("test_user")

    mock_redis.get_posts_by_username.assert_called_once_with("test_user")


@pytest.mark.asyncio
async def test_ensure_delay_with_posts_needs_wait(mock_redis, mock_time):
    """Тест: если последний пост был недавно, функция должна ждать."""
    past_timestamp = int(datetime(2023, 1, 1).timestamp())
    mock_posts = [
        Post(id="1", text="Recent post", sender_username="test_user", timestamp=past_timestamp)
    ]
    mock_redis.get_posts_by_username.return_value = mock_posts
    mock_time.return_value = past_timestamp + 30

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await ensure_delay_between_posts("test_user", delay=60)
        mock_sleep.assert_awaited_once_with(30)


def test_decode_redis_bytes():
    assert decode_redis(b"hello") == "hello"


def test_decode_redis_list():
    assert decode_redis([b"a", b"b"]) == ["a", "b"]


def test_decode_redis_dict():
    assert decode_redis({b"key": b"value"}) == {"key": "value"}


def test_decode_redis_unsupported_type():
    with pytest.raises(Exception, match="type not handled"):
        decode_redis(123)
