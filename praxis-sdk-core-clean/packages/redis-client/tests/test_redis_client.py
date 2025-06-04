import pytest
from unittest.mock import MagicMock, patch, call, AsyncMock
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

        mock_redis.set.return_value = True
        mock_redis.delete.return_value = 1
        mock_redis.get.return_value = None

        mock_redis.reset_mock()
        return db


def test_redis_initialization(redis_db, mock_redis):
    assert isinstance(redis_db.r, MagicMock)


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
    mock_redis.reset_mock()
    redis_db.set("test_key", {"key": "value"})
    mock_redis.set.assert_called_once_with("test_key", json.dumps({"key": "value"}), keepttl=False)


def test_set_with_none(redis_db, mock_redis):
    mock_redis.reset_mock()
    redis_db.set("test_key", None)
    mock_redis.delete.assert_called_once_with("test_key")


def test_setex(redis_db, mock_redis):
    redis_db.setex("test_key", {"key": "value"}, 60)
    mock_redis.setex.assert_called_once_with("test_key", 60, json.dumps({"key": "value"}))


def test_delete(redis_db, mock_redis):
    mock_redis.reset_mock()
    redis_db.delete("test_key")
    mock_redis.delete.assert_called_once_with("test_key")


def test_get_keys_by_pattern(redis_db, mock_redis):
    mock_redis.scan_iter.return_value = [b"key1", b"key2"]
    assert redis_db.get_keys_by_pattern("pattern") == ["key1", "key2"]


def test_parse_list_with_list(redis_db, mock_redis):
    mock_redis.get.return_value = ["a", "b"]
    assert redis_db.parse_list("test") == ["a", "b"]


def test_parse_list_with_string(redis_db, mock_redis):
    mock_redis.get.return_value = "a,b,c"
    assert redis_db.parse_list("test") == ["a", "b", "c"]


def test_parse_list_with_empty_string(redis_db, mock_redis):
    mock_redis.get.return_value = ""
    assert redis_db.parse_list("test") == []


def test_parse_list_with_none(redis_db, mock_redis):
    mock_redis.get.return_value = None
    assert redis_db.parse_list("test") == []


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


def test_get_user_posts_by_create_time(redis_db, mock_redis):
    post_data = json.dumps({"id": "1", "text": "test", "sender_username": "user", "timestamp": 123})
    mock_redis.zrangebyscore.return_value = [post_data.encode()]
    posts = redis_db.get_user_posts_by_create_time("user", 3600)
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


def test_add_send_partnership(redis_db, mock_redis):
    redis_db.add_send_partnership("user", "partner")
    mock_redis.zadd.assert_called_once_with(
        'send_partnership:user',
        {'partner': pytest.approx(time.time(), rel=1)}
    )


def test_get_send_partnership(redis_db, mock_redis):
    mock_redis.zrange.return_value = [b"partner1", b"partner2"]
    assert redis_db.get_send_partnership("user") == ["partner1", "partner2"]


def test_get_account_last_action_time(redis_db, mock_redis):
    mock_redis.get.return_value = "123.45"
    assert redis_db.get_account_last_action_time("user", "action") == 123.45


def test_update_account_last_action_time(redis_db, mock_redis):
    redis_db.update_account_last_action_time("user", "action", 123.45)
    mock_redis.set.assert_called_once_with("action:user", 123.45)


def test_is_account_active(redis_db, mock_redis):
    mock_redis.exists.return_value = True
    assert redis_db.is_account_active("user") is True


def test_save_tweet_link(redis_db, mock_redis):
    redis_db.save_tweet_link("function", "123")
    mock_redis.rpush.assert_called_once_with(
        "created_tweet:function",
        "https://twitter.com/i/web/status/123"
    )


@pytest.fixture
def prompt_manager(redis_db):
    with patch('redis_client.main.get_redis_db', return_value=redis_db):
        return PromptManager(redis_db)


def test_prompt_manager_singleton(prompt_manager, redis_db):
    with patch('redis_client.main.get_redis_db', return_value=redis_db):
        manager1 = PromptManager(redis_db)
        manager2 = PromptManager(redis_db)
        assert manager1 is manager2


def test_get_prompt(prompt_manager, redis_db, mock_redis):
    mock_redis.get.return_value = json.dumps("test prompt")
    assert prompt_manager.get_prompt("test_func") == "test prompt"
    mock_redis.get.assert_called_once_with("prompt:test_func")


def test_get_prompt_with_default(prompt_manager, redis_db, mock_redis):
    mock_redis.get.return_value = None
    with pytest.raises(ValueError):
        prompt_manager.get_prompt("nonexistent_func")


def test_extract_fstring_vars(prompt_manager):
    template = "Hello {name}, welcome to {project}"
    assert prompt_manager._extract_fstring_vars(template) == {"name", "project"}


@pytest.mark.asyncio
async def test_ensure_delay_between_posts_no_wait(redis_db, mock_redis):
    mock_redis.zrangebyscore.return_value = []
    await ensure_delay_between_posts("user")


@pytest.mark.asyncio
async def test_ensure_delay_between_posts_with_wait(redis_db, mock_redis):
    post_data = json.dumps({"id": "1", "text": "test", "sender_username": "user", "timestamp": time.time() - 60})
    mock_redis.zrangebyscore.return_value = [post_data.encode()]

    with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
        await ensure_delay_between_posts("user", delay=300)
        mock_sleep.assert_awaited_once()


def test_decode_redis_bytes():
    assert decode_redis(b"test") == "test"


def test_decode_redis_list():
    assert decode_redis([b"a", b"b"]) == ["a", "b"]


def test_decode_redis_dict():
    assert decode_redis({b"key": b"value"}) == {"key": "value"}


def test_decode_redis_unknown_type():
    with pytest.raises(Exception) as exc_info:
        decode_redis(123)
    assert "type not handled" in str(exc_info.value).lower()


def test_set_default_when_key_exists(redis_db, mock_redis):
    mock_redis.get.return_value = "existing_value"
    redis_db.set_default("test_key", "default_value")
    mock_redis.set.assert_not_called()


def test_set_default_when_key_empty(redis_db, mock_redis):
    mock_redis.get.return_value = ""
    redis_db.set_default("test_key", "default_value")
    mock_redis.set.assert_called_once_with("test_key", json.dumps("default_value"), keepttl=False)


def test_set_default_when_key_none(redis_db, mock_redis):
    mock_redis.get.return_value = None
    redis_db.set_default("test_key", "default_value")
    mock_redis.set.assert_called_once_with("test_key", json.dumps("default_value"), keepttl=False)


def test_get_item_dunder(redis_db, mock_redis):
    mock_redis.get.return_value = b'{"key": "value"}'
    result = redis_db["test_key"]
    assert result == {"key": "value"}


def test_set_item_dunder(redis_db, mock_redis):
    redis_db["test_key"] = {"key": "value"}
    mock_redis.set.assert_called_once_with("test_key", json.dumps({"key": "value"}), keepttl=False)


def test_del_item_dunder(redis_db, mock_redis):
    del redis_db["test_key"]
    mock_redis.delete.assert_called_once_with("test_key")


def test_get_keys_by_pattern_blocking(redis_db, mock_redis):
    mock_redis.keys.return_value = [b"key1", b"key2"]
    result = redis_db.get_keys_by_pattern_blocking("pattern")
    assert result == ["key1", "key2"]


def test_get_twitter_data_keys(redis_db, mock_redis):
    mock_redis.scan_iter.return_value = [b"twitter_data:user1", b"twitter_data:user2"]
    result = redis_db.get_twitter_data_keys()
    assert result == ["twitter_data:user1", "twitter_data:user2"]


def test_add_to_sorted_set(redis_db, mock_redis):
    redis_db.add_to_sorted_set("test_key", 100, "value")
    mock_redis.zadd.assert_called_once_with("test_key", {"value": 100})


def test_get_sorted_set(redis_db, mock_redis):
    mock_redis.zrange.return_value = [b"value1", b"value2"]
    result = redis_db.get_sorted_set("test_key")
    assert result == ["value1", "value2"]


def test_get_function_variables(redis_db, mock_redis):
    result = redis_db.get_function_variables()
    assert isinstance(result, dict)
    mock_redis.set.assert_called_once()


def test_wait_for_redis_success(redis_db, mock_redis):
    mock_redis.set.return_value = True
    mock_redis.delete.return_value = 1
    assert redis_db.wait_for_redis(1) is True


def test_wait_for_redis_failure(redis_db, mock_redis):
    mock_redis.set.side_effect = redis.exceptions.ConnectionError()
    assert redis_db.wait_for_redis(1) is False


def test_wait_for_redis_busy_loading(redis_db, mock_redis):
    mock_redis.set.side_effect = redis.exceptions.BusyLoadingError()
    assert redis_db.wait_for_redis(1) is False
