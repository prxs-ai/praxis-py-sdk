# fmt: off
import json
import os
import time
from typing import Any, List
from dataclasses import dataclass
from dataclasses import asdict

from typing import Set
import inspect
from functools import wraps
import asyncio
import redis

from infrastructure.configs.logger import configure_logging, get_logger
from schemas.knowledgebase.knowledgetype import KnowledgeType

configure_logging()
logger = get_logger(__name__)


@dataclass
class Post:
    id: str
    text: str
    sender_username: str
    timestamp: int
    quoted_tweet_id: str | None = None
    is_reply_to: str | None = None
    is_news_summary_tweet: bool = False


class RedisDB:
    """
    A class for interacting with a Redis database.

    It connects to Redis based on the environment variables:
        REDIS_HOST (str): Redis host (default: 'localhost')
        REDIS_PORT (int): Redis port (default: 6379)
        REDIS_DB (int): Redis database index (default: 0)
    """
    _NO_DEFAULT = object()

    def __init__(self) -> None:
        """
        Initialize the Redis connection.
        """
        logger.info(
            f'Redis: {os.environ.get("REDIS_HOST", "localhost")}:{os.environ.get("REDIS_PORT", 6379)} '
            f'db={os.environ.get("REDIS_DB", 0)}'
        )
        self.r = redis.Redis(
            host=os.environ.get('REDIS_HOST', 'localhost'),
            port=int(os.environ.get('REDIS_PORT', 6379)),
            db=int(os.environ.get('REDIS_DB', 0))  # 0 - main, 1 - test
        )

        if self.wait_for_redis(timeout=100):
            logger.info('Redis connected')
        else:
            logger.error('Failed to connect to Redis after the timeout.')
            raise ConnectionError('Failed to connect to Redis.')

    def add_to_set(self, key: str, value: str) -> None:
        """
        Add a value to a Redis set at the given key.
        """
        self.r.sadd(key, value)

    def get_set(self, key: str) -> List[str]:
        """
        Retrieve all members of a Redis set as a list of strings.
        """
        return [item.decode('utf-8') for item in self.r.smembers(key)]

    def wait_for_redis(self, timeout: int) -> bool:
        """
        Wait for Redis to become available within the given timeout in seconds.

        Returns True if successful, otherwise False.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                self.r.set('__temp_test_key__', 'value')
                self.r.delete('__temp_test_key__')
                return True
            except redis.exceptions.BusyLoadingError:
                logger.info('Redis is still loading. Waiting...')
                time.sleep(1)
            except redis.exceptions.ConnectionError as e:
                logger.info(f'Redis is not available {type(e)=}, {e=}. Waiting...')
                time.sleep(1)
            except Exception as e:
                logger.exception(f"An unexpected error occurred: {type(e)} {e}")
                if 'Temporary failure in name resolution' in str(e):
                    logger.info('Temporary failure in name resolution. Waiting...')
                    time.sleep(1)
                else:
                    return False
        return False

    def get(self, key: str, default: Any = _NO_DEFAULT) -> Any:
        """
        Get the value for the given key. The stored data is expected to be JSON.

        If the key does not exist and a default is provided, return that default.
        """
        v = self.r.get(key)
        if not v and default is not self._NO_DEFAULT:
            return default
        if v is None:
            return None
        return json.loads(v)

    def set(self, key: str, value: Any, log: bool = True, keep_ttl: bool = False) -> None:
        """
        Set the value for the given key, serializing the value to JSON.

        If value is None, the key will be deleted.

        Args:
            keep_ttl (bool): If True, the current TTL is preserved.
        """
        if log:
            logger.info(f'Set {key} to {value}')
        if value is None:
            self.r.delete(key)
        else:
            self.r.set(key, json.dumps(value), keepttl=keep_ttl)

    def setex(self, key: str, value: Any, ex: int, log: bool = True) -> None:
        """
        Set the value for the given key with an expiration time (in seconds).

        If value is None, the key will be deleted.
        """
        if log:
            logger.info(f'Set EXPIRY {key} to {value}, expiry: {ex}')
        if value is None:
            logger.warning(f'Set EXPIRY value is None, deleting {key}')
            self.r.delete(key)
        else:
            self.r.setex(key, ex, json.dumps(value))

    def set_default(self, key: str, value: Any) -> None:
        """
        Set a default value if the key does not exist or is empty.
        """
        existing_value = self.get(key)
        if existing_value is None or existing_value == '':
            if value:
                self.set(key, value)

    def delete(self, key: str, log: bool = True) -> None:
        """
        Delete the given key.
        """
        if log:
            logger.info(f'Delete {key}')
        self.r.delete(key)

    def get_keys_by_pattern(self, pattern: str) -> List[str]:
        """
        Retrieve a list of keys matching the given pattern using SCAN.
        """
        result = []
        for key in self.r.scan_iter(pattern):
            result.append(key.decode('utf-8'))
        return result

    def get_keys_by_pattern_blocking(self, pattern: str) -> List[str]:
        """
        Retrieve a list of keys matching the pattern using KEYS command.

        Note: This is a blocking operation and not recommended for large databases.
        """
        return [key.decode('utf-8') for key in self.r.keys(pattern)]

    def __getitem__(self, item: str) -> Any:
        return self.get(item)

    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value)

    def __delitem__(self, key: str) -> None:
        self.delete(key)

    def parse_list(self, key: str) -> List[str]:
        """
        Retrieve the value by key as a list.

        If the value is already a list, return it as is.
        If it's a string, split by comma.
        If it's None or empty, return an empty list.
        """
        chat_ids = self[key]
        if isinstance(chat_ids, list):
            return chat_ids
        if chat_ids is None:
            return []
        if isinstance(chat_ids, str):
            if chat_ids in ['-', '']:
                return []
            else:
                return chat_ids.split(',')
        raise ValueError(f'Unknown type of chat_ids: {type(chat_ids)} {chat_ids=}')

    def get_twitter_data_keys(self):
        keys = []
        for key in self.r.scan_iter(match="twitter_data:*"):
            keys.append(key)
        return [k.decode() for k in keys]

    def add_to_sorted_set(self, key: str, score: int, value: str):
        self.r.zadd(key, {value: score})

    def get_sorted_set(self, key: str, start: int = 0, end: int = -1):
        return [item.decode('utf-8') for item in self.r.zrange(key, start, end)]

    def add_user_post(self, username: str, post: Post):
        post_json = json.dumps(asdict(post))
        self.add_to_sorted_set(f'posted_tweets:{username}', post.timestamp, post_json)

    def get_user_posts(self, username: str) -> list[Post]:
        posts = self.get_sorted_set(f'posted_tweets:{username}')
        return [Post(**json.loads(post)) for post in posts]

    def get_user_posts_by_create_time(self, username: str, second_ago: int = 3 * 60 * 60) -> list[Post]:
        """Newest in the end of list"""
        current_timestamp = int(time.time())
        min_score = current_timestamp - second_ago
        posts = self.r.zrangebyscore(f'posted_tweets:{username}', min_score, current_timestamp)
        return [Post(**json.loads(post)) for post in posts]

    def add_send_partnership(self, username: str, partner_user_id: str):
        self.add_to_sorted_set(f'send_partnership:{username}', int(time.time()), partner_user_id)

    def get_send_partnership(self, username: str) -> list[str]:
        return self.get_sorted_set(f'send_partnership:{username}')

    def get_active_twitter_accounts(self) -> list[str]:
        """Получаем все активные твиттер аккаунты"""
        accounts = []
        for key in self.get_keys_by_pattern("twitter_data:*"):
            username = key.split(":")[1]
            accounts.append(username)
        return accounts

    def get_account_last_action_time(self, username: str, action_type: str) -> float:
        """Получаем время последнего действия для аккаунта"""
        key = f"{action_type}:{username}"
        return float(self.get(key) or 0)

    def update_account_last_action_time(self, username: str, action_type: str, timestamp: float):
        """Обновляем время последнего действия для аккаунта"""
        key = f"{action_type}:{username}"
        self.set(key, timestamp)

    def is_account_active(self, username: str) -> bool:
        """Проверяем активен ли аккаунт"""
        return bool(self.r.exists(f"twitter_data:{username}"))

    def remove_account(self, username: str):
        """Удаляем все данные аккаунта"""
        # Удаляем основные данные аккаунта
        self.delete(f"twitter_data:{username}")

        # Удаляем все временные метки
        for action_type in [
            "last_create_post_time",
            "last_gorilla_marketing_time",
            "last_likes_time",
            "last_comment_agix_time",
            "last_answer_my_comment_time",
            "last_answer_comment_time"
        ]:
            self.delete(f"{action_type}:{username}")

        # Удаляем историю постов
        self.delete(f"posted_tweets:{username}")

        # Удаляем историю ответов
        self.delete(f"gorilla_marketing_answered:{username}")

        logger.info(f"Account {username} removed from Redis")


# Initialize a default instance
db = RedisDB()


def get_redis_db() -> RedisDB:
    return db


class PromptManager:
    def __init__(self, redis_db: RedisDB):
        self.redis = redis_db
        self.prompt_cache = {}
        self._start_subscriber()

    def _start_subscriber(self):
        """Запускает Redis подписчика для отслеживания обновлений промптов"""
        pubsub = self.redis.r.pubsub()
        pubsub.subscribe('prompt_updates')

        async def listener():
            while True:
                try:
                    message = pubsub.get_message()
                    if message and message['type'] == 'message':
                        prompt_key = message['data'].decode('utf-8')
                        if prompt_key in self.prompt_cache:
                            del self.prompt_cache[prompt_key]
                            logger.info(f"Промпт обновлен: {prompt_key}")
                except Exception as e:
                    logger.error(f"Ошибка в pub/sub listener: {e}")
                await asyncio.sleep(0.1)

        asyncio.create_task(listener())

    def get_prompt(self, function_name: str) -> str:
        """Получает актуальный промпт для функции из Redis"""
        if function_name not in self.prompt_cache:
            prompt = self.redis.get(f'prompt:{function_name}')
            if not prompt:
                prompt = DEFAULT_PROMPTS.get(function_name, "")
                if prompt:
                    self.redis.set(f'prompt:{function_name}', prompt)
                else:
                    raise ValueError(f"Промпт для функции {function_name} не найден")
            self.prompt_cache[function_name] = prompt
        return self.prompt_cache[function_name]


class PromptFormatter:
    """Класс для форматирования промптов с поддержкой внутренних переменных"""

    def __init__(self, function_name: str, template: str):
        self.function_name = function_name
        self.template = template

    async def format(self, func, args, kwargs) -> str:
        # Получаем значения аргументов функции
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()
        format_dict = dict(bound_args.arguments)

        # Выполняем функцию для получения внутренних переменных
        result = await func(*args, **kwargs)

        # Добавляем внутренние переменные в словарь форматирования
        if isinstance(result, tuple) and len(result) == 2:
            internal_vars, final_result = result
            format_dict.update(internal_vars)

        try:
            formatted_prompt = self.template.format(**format_dict)
            return formatted_prompt, final_result
        except KeyError as e:
            logger.error(f"Отсутствует переменная для форматирования промпта: {e}")
            raise


def get_internal_variables(func_name: str) -> Set[str]:
    """Возвращает список внутренних переменных, которые создаются внутри функции"""
    internal_vars = {
        'create_comment_to_post': {'relevant_knowledge'},
        'create_comment_to_comment': {'relevant_knowledge'},
        # Добавьте другие функции и их внутренние переменные
    }
    return internal_vars.get(func_name, set())


def use_dynamic_prompt(function_name: str):
    """Декоратор для использования динамических промптов из Redis с поддержкой внутренних переменных"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            prompt_manager = PromptManager(db)
            template = prompt_manager.get_prompt(function_name)

            async def modified_func(*args, **kwargs):
                if 'relevant_knowledge' in get_internal_variables(function_name):
                    # Получаем knowledge_base и query из аргументов
                    bound_args = inspect.signature(func).bind(*args, **kwargs)
                    bound_args.apply_defaults()
                    knowledge_base = bound_args.arguments.get('knowledge_base')
                    # query = bound_args.arguments.get('twitter_post') or bound_args.arguments.get('comment_text')
                    query = 'What is the project about?'
                    # Получаем relevant_knowledge
                    relevant_knowledge = await knowledge_base.search_knowledge(
                        query=query,
                        k=2,
                        # knowledge_type=KnowledgeType.PROJECT_INFO
                    )

                    return {'relevant_knowledge': relevant_knowledge}, None

                return {}, None

            formatter = PromptFormatter(function_name, template)
            formatted_prompt, _ = await formatter.format(modified_func, args, kwargs)

            kwargs['prompt'] = formatted_prompt
            return await func(*args, **kwargs)

        return wrapper

    return decorator


DEFAULT_PROMPTS = {
    'create_comment_to_post': """You are an AI and crypto enthusiast...
TWITTER POST: {twitter_post}
Context from knowledge base: {relevant_knowledge}
""",
    'create_comment_to_comment': """You are a technology community manager...
Conversation to respond to: {comment_text}
Context from knowledge base: {relevant_knowledge}
"""
}

prompt_manager = PromptManager(db)