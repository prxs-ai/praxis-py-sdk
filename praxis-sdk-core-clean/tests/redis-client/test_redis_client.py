import pytest
from unittest.mock import MagicMock, patch, call
import json
import time
from datetime import datetime
import redis
from redis_client.main import RedisDB, Post, PromptManager, use_dynamic_prompt, ensure_delay_between_posts, decode_redis


@pytest.fixture
def mock_redis():
    return MagicMock(spec=redis.Redis)


@pytest.fixture
def redis_db(mock_redis):
    with patch('redis_client.main.settings') as mock_settings, \
            patch('redis.Redis', return_value=mock_redis):
        mock_settings.REDIS_HOST = "localhost"
        mock_settings.REDIS_PORT = 6379
        mock_settings.REDIS_DB = 0
        mock_settings.VECTOR_DIMENSION = 384

        db = RedisDB()
        db.r = mock_redis
        return db


def test_redis_initialization(redis_db, mock_redis):
    assert isinstance(redis_db.r, MagicMock)
    mock_redis.set.assert_called_once_with('__temp_test_key__', 'value')
    mock_redis.delete.assert_called_once_with('__temp_test_key__')


def test_add_to_set(redis_db, mock_redis):
    redis_db.add_to_set("test_key", "value")
    mock_redis.sadd.assert_called_once_with("test_key", "value")


def test_get_set(redis_db, mock_redis):
    mock_redis.smembers.return_value = [b"value1", b"value2"]
    result = redis_db.get_set("test_key")
    assert result == ["value1", "value2"]
    mock_redis.smembers.assert_called_once_with("test_key")


def test_get(redis_db, mock_redis):
    mock_redis.get.return_value = b'{"key": "value"}'
    assert redis_db.get("test_key") == {"key": "value"}

    mock_redis.get.return_value = None
    assert redis_db.get("nonexistent", "default") == "default"


def test_set(redis_db, mock_redis):
    redis_db.set("test_key", {"key": "value"})
    mock_redis.set.assert_called_once_with("test_key", json.dumps({"key": "value"}), keepttl=False)

    mock_redis.reset_mock()
    redis_db.set("test_key", None)
    mock_redis.delete.assert_called_once_with("test_key")


def test_setex(redis_db, mock_redis):
    redis_db.setex("test_key", {"key": "value"}, 60)
    mock_redis.setex.assert_called_once_with("test_key", 60, json.dumps({"key": "value"}))


def test_delete(redis_db, mock_redis):
    redis_db.delete("test_key")
    mock_redis.delete.assert_called_once_with("test_key")


def test_get_keys_by_pattern(redis_db, mock_redis):
    mock_redis.scan_iter.return_value = [b"key1", b"key2"]
    assert redis_db.get_keys_by_pattern("pattern") == ["key1", "key2"]


def test_parse_list(redis_db):
    redis_db.get = lambda k: None
    assert redis_db.parse_list("test") == []

    redis_db.get = lambda k: ""
    assert redis_db.parse_list("test") == []

    redis_db.get = lambda k: "a,b,c"
    assert redis_db.parse_list("test") == ["a", "b", "c"]

    redis_db.get = lambda k: ["a", "b"]
    assert redis_db.parse_list("test") == ["a", "b"]


def test_add_user_post(redis_db, mock_redis):
    post = Post(id="1", text="test", sender_username="user", timestamp=123)
    redis_db.add_user_post("user", post)
    mock_redis.zadd.assert_called_once_with(
        'posted_tweets:user',
        {json.dumps({"id": "1", "text": "test", "sender_username": "user",
                     "timestamp": 123, "quoted_tweet_id": None,
                     "is_reply_to": None, "is_news_summary_tweet": False}): 123}
    )


def test_get_user_posts(redis_db, mock_redis):
    post_data = json.dumps({"id": "1", "text": "test", "sender_username": "user", "timestamp": 123})
    mock_redis.zrange.return_value = [post_data.encode()]
    posts = redis_db.get_user_posts("user")
    assert len(posts) == 1
    assert posts[0].id == "1"


def test_get_active_twitter_accounts(redis_db, mock_redis):
    mock_redis.scan_iter.return_value = [b"twitter_data:user1", b"twitter_data:user2"]
    assert redis_db.get_active_twitter_accounts() == ["user1", "user2"]


def test_remove_account(redis_db, mock_redis):
    redis_db.remove_account("user")
    calls = [
        call("twitter_data:user"),
        call("last_create_post_time:user"),
        call("last_gorilla_marketing_time:user"),
        call("last_likes_time:user"),
        call("last_comment_agix_time:user"),
        call("last_answer_my_comment_time:user"),
        call("last_answer_comment_time:user"),
        call("posted_tweets:user"),
        call("gorilla_marketing_answered:user")
    ]
    mock_redis.delete.assert_has_calls(calls, any_order=True)


@pytest.fixture
def prompt_manager(redis_db):
    with patch('redis_client.main.get_redis_db', return_value=redis_db):
        return PromptManager(redis_db)


def test_prompt_manager_singleton(prompt_manager):
    with patch('redis_client.main.get_redis_db') as mock_get_redis:
        manager1 = PromptManager(mock_get_redis())
        manager2 = PromptManager(mock_get_redis())
        assert manager1 is manager2


def test_get_prompt(prompt_manager, redis_db):
    redis_db.get = lambda k: "test prompt" if k == "prompt:test_func" else None
    assert prompt_manager.get_prompt("test_func") == "test prompt"


def test_get_prompt_with_default(prompt_manager, redis_db):
    redis_db.get = lambda k: None
    with pytest.raises(ValueError):
        prompt_manager.get_prompt("nonexistent_func")


@pytest.mark.asyncio
async def test_ensure_delay_between_posts_no_wait():
    with patch('redis_client.main.RedisDB.get_user_posts_by_create_time') as mock_get_posts:
        mock_get_posts.return_value = []
        await ensure_delay_between_posts("user")


@pytest.mark.asyncio
async def test_ensure_delay_between_posts_with_wait():
    post = Post(id="1", text="test", sender_username="user", timestamp=time.time() - 60)
    with patch('redis_client.main.RedisDB.get_user_posts_by_create_time') as mock_get_posts, \
            patch('asyncio.sleep') as mock_sleep:
        mock_get_posts.return_value = [post]
        await ensure_delay_between_posts("user", delay=300)
        mock_sleep.assert_awaited_once()


def test_decode_redis_bytes():
    assert decode_redis(b"test") == "test"


def test_decode_redis_list():
    assert decode_redis([b"a", b"b"]) == ["a", "b"]


def test_decode_redis_dict():
    assert decode_redis({b"key": b"value"}) == {"key": "value"}


def test_decode_redis_unknown_type():
    with pytest.raises(Exception, match="type not handled"):
        decode_redis(123)
