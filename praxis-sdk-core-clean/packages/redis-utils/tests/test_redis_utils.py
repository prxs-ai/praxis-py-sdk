import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from loguru import logger

from redis_utils.main import ensure_delay_between_posts, decode_redis
from redis_client.main import Post


# Фикстура для мокирования Redis
@pytest.fixture
def mock_redis():
    with patch("redis_utils.main.db") as mock_db:
        yield mock_db


# Тесты для ensure_delay_between_posts
@pytest.mark.asyncio
async def test_ensure_delay_no_posts(mock_redis):
    """Тест: если постов нет, функция не должна ждать."""
    mock_redis.get_posts_by_username.return_value = []

    await ensure_delay_between_posts("test_user")

    mock_redis.get_posts_by_username.assert_called_once_with("test_user")


@pytest.mark.asyncio
async def test_ensure_delay_with_posts_no_wait(mock_redis):
    """Тест: если последний пост был давно, ждать не нужно."""
    past_timestamp = int(datetime(2023, 1, 1).timestamp())
    mock_posts = [
        Post(id="1", text="Old post", sender_username="test_user", timestamp=past_timestamp)
    ]
    mock_redis.get_posts_by_username.return_value = mock_posts

    with patch("time.time", return_value=past_timestamp + 1000):  # Прошло много времени
        await ensure_delay_between_posts("test_user", delay=60)

    mock_redis.get_posts_by_username.assert_called_once_with("test_user")


@pytest.mark.asyncio
async def test_ensure_delay_with_posts_needs_wait(mock_redis):
    """Тест: если последний пост был недавно, функция должна ждать."""
    past_timestamp = int(datetime(2023, 1, 1).timestamp())
    mock_posts = [
        Post(id="1", text="Recent post", sender_username="test_user", timestamp=past_timestamp)
    ]
    mock_redis.get_posts_by_username.return_value = mock_posts

    with patch("time.time", return_value=past_timestamp + 30):  # Прошло мало времени
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await ensure_delay_between_posts("test_user", delay=60)
            mock_sleep.assert_awaited_once_with(30)  # Ожидаем 60 - 30 = 30 сек


# Тесты для decode_redis
def test_decode_redis_bytes():
    """Тест: декодирование bytes в строку."""
    assert decode_redis(b"hello") == "hello"


def test_decode_redis_list():
    """Тест: декодирование списка."""
    assert decode_redis([b"a", b"b"]) == ["a", "b"]


def test_decode_redis_dict():
    """Тест: декодирование словаря."""
    assert decode_redis({b"key": b"value"}) == {"key": "value"}


def test_decode_redis_unsupported_type():
    """Тест: ошибка при неподдерживаемом типе."""
    with pytest.raises(Exception, match="type not handled"):
        decode_redis(123)  # int не поддерживается