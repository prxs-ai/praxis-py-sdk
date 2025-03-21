import json
import threading
import time
from random import random
from typing import Any, List
from dataclasses import dataclass
from dataclasses import asdict
import asyncio
from random import randint
from datetime import datetime
from typing import Set
import inspect
from functools import wraps
import redis
from redis_client.config import get_settings

settings = get_settings()


@dataclass
class Post:
    id: str
    text: str
    sender_username: str
    timestamp: int
    quoted_tweet_id: str | None = None
    is_reply_to: str | None = None
    is_news_summary_tweet: bool = False

FUNCTION_VARIABLES = {
    'create_comment_to_post': {'twitter_post', 'relevant_knowledge'},
    'create_comment_to_comment': {'comment_text', 'relevant_knowledge'},
    'create_tweet': {'project_tweets', 'my_tweets', 'relevant_knowledge'},
    'create_quoted_tweet': {'tweet_for_quote', 'my_tweets', 'relevant_knowledge'},
    'create_news_tweet': {'news_tweets', 'my_tweets', 'relevant_knowledge'},
    'check_answer_is_needed': {'twitter_comment'},
    'check_tweet_for_marketing': {'tweet_text', 'relevant_knowledge'},
    'create_marketing_comment': {'tweet_text', 'relevant_knowledge', 'question_prompt'},
}

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
        REDIS_HOST = settings.REDIS_HOST if settings.REDIS_HOST else "localhost"
        REDIS_PORT = settings.REDIS_PORT if settings.REDIS_PORT else 6379
        REDIS_DB = settings.REDIS_DB if settings.REDIS_DB else 0
        print(
            f'Redis: {REDIS_HOST}:{REDIS_PORT} '
            f'db={REDIS_DB}'
        )
        self.r = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB  # 0 - main, 1 - test
        )

        if self.wait_for_redis(timeout=100):
            print('Redis connected')
        else:
            print('Failed to connect to Redis after the timeout.')
            raise ConnectionError('Failed to connect to Redis.')
        self._save_function_variables_on_startup()

    def _save_function_variables_on_startup(self):
        function_vars_dict = {key: list(value) for key, value in FUNCTION_VARIABLES.items()}
        self.set("function_variables", function_vars_dict, log=False)

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
                print('Redis is still loading. Waiting...')
                time.sleep(1)
            except redis.exceptions.ConnectionError as e:
                repr(e)
                time.sleep(1)
            except Exception as e:
                repr(e)
                if 'Temporary failure in name resolution' in str(e):
                    print('Temporary failure in name resolution. Waiting...')
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
            print(f'Set {key} to {value}')
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
            print(f'Set EXPIRY {key} to {value}, expiry: {ex}')
        if value is None:
            print(f'Set EXPIRY value is None, deleting {key}')
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
            print(f'Delete {key}')
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

        print(f"Account {username} removed from Redis")

    def get_function_variables(self) -> dict[str, list[str]]:

        function_vars_dict = {key: list(value) for key, value in FUNCTION_VARIABLES.items()}

        # Сохраняем в Redis
        self.set("function_variables", function_vars_dict)

        # И возвращаем то, что записали
        return function_vars_dict

    def save_tweet_link(self, function_name: str, tweet_id: str) -> None:
        """Сохраняет ссылку на твит для конкретной функции"""
        key = f"created_tweet:{function_name}"
        link = f"https://twitter.com/i/web/status/{tweet_id}"
        self.r.rpush(key, link)


def get_redis_db(*args, **kwargs) -> RedisDB:
    return RedisDB(*args, **kwargs)


class PromptManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, redis_db: RedisDB):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(PromptManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, redis_db: RedisDB):
        if self._initialized:
            return

        self.redis = redis_db
        self.prompt_cache = {}
        self._subscriber_thread = None
        self._running = True
        self._start_subscriber_thread()
        self._initialized = True

    def _start_subscriber_thread(self):
        """Запускает Redis подписчика в отдельном потоке"""

        def subscriber_worker():
            pubsub = self.redis.r.pubsub()
            pubsub.subscribe('prompt_updates')

            while self._running:
                try:
                    message = pubsub.get_message()
                    if message and message['type'] == 'message':
                        prompt_key = message['data'].decode('utf-8')
                        if prompt_key in self.prompt_cache:
                            del self.prompt_cache[prompt_key]
                            print(f"Промпт обновлен: {prompt_key}")
                except Exception as e:
                    print(f"Ошибка в subscriber_worker: {e}")
                time.sleep(0.1)

            pubsub.close()

        self._subscriber_thread = threading.Thread(
            target=subscriber_worker,
            daemon=True
        )
        self._subscriber_thread.start()

    def get_prompt(self, function_name: str) -> str:
        """Получает актуальный промпт для функции из Redis"""
        # Добавляем префикс к ключу
        redis_key = f'prompt:{function_name}'

        if redis_key not in self.prompt_cache:
            prompt = self.redis.get(redis_key)
            if not prompt:
                prompt = DEFAULT_PROMPTS.get(function_name, "")
                if prompt:
                    # Проверяем, что в промпте используются только разрешенные переменные
                    variables = self._extract_fstring_vars(prompt)
                    allowed_vars = FUNCTION_VARIABLES.get(function_name, set())
                    if not variables.issubset(allowed_vars):
                        invalid_vars = variables - allowed_vars
                        raise ValueError(
                            f"Промпт для {function_name} содержит недопустимые переменные: {invalid_vars}. "
                            f"Разрешенные переменные: {allowed_vars}"
                        )
                    self.redis.set(redis_key, prompt)
                else:
                    raise ValueError(f"Промпт для функции {function_name} не найден")
            self.prompt_cache[redis_key] = prompt
        return self.prompt_cache[redis_key]

    @staticmethod
    def _extract_fstring_vars(template: str) -> Set[str]:
        """Extract variable names from f-string"""
        import re
        pattern = r'{([^{}:]+)(?::[^{}]+)?}'
        return set(re.findall(pattern, template))

    def __del__(self):
        self._running = False
        if self._subscriber_thread and self._subscriber_thread.is_alive():
            self._subscriber_thread.join(timeout=1.0)


def use_dynamic_prompt(function_name: str):
    """Декоратор для использования динамических промптов из Redis"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            prompt_manager = PromptManager(get_redis_db())
            template = prompt_manager.get_prompt(function_name)

            # Проверяем разрешенные переменные
            variables = prompt_manager._extract_fstring_vars(template)
            allowed_vars = FUNCTION_VARIABLES.get(function_name, set())
            if not variables.issubset(allowed_vars):
                invalid_vars = variables - allowed_vars
                raise ValueError(
                    f"Промпт для {function_name} содержит недопустимые переменные: {invalid_vars}. "
                    f"Разрешенные переменные: {allowed_vars}"
                )

            # Получаем значения параметров функции
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            format_dict = dict(bound_args.arguments)

            if function_name == 'check_tweet_for_marketing' and 'tweets' in format_dict:
                kwargs['prompt'] = template
                return await func(*args, **kwargs)

            if function_name == 'create_marketing_comment':
                format_dict['question_prompt'] = " or sometimes combine your thoughts with a relevant question." if random() < 0.45 else ""

            if 'relevant_knowledge' in variables:
                knowledge_base = bound_args.arguments.get('knowledge_base')
                query = "What is the project about?"
                if knowledge_base and query:
                    relevant_knowledge = await knowledge_base.search_knowledge(
                        query=query,
                        k=2,
                    )
                    format_dict['relevant_knowledge'] = relevant_knowledge

            try:
                formatted_prompt = template.format(**format_dict)
                kwargs['prompt'] = formatted_prompt
                return await func(*args, **kwargs)
            except KeyError as e:
                print(f"Отсутствует переменная для форматирования промпта: {e}")
                raise ValueError(
                    f"В промпте для {function_name} отсутствует значение для переменной {e}. "
                    f"Проверьте, что все необходимые параметры переданы в функцию."
                )
            except Exception as e:
                print(f"Ошибка при применении промпта для {function_name}: {e}")
                raise

        return wrapper
    return decorator


# Дефолтные промпты
DEFAULT_PROMPTS = {
    'create_comment_to_post': """DONT USE HASHTAG You are an AI and crypto enthusiast with a vision for the future of decentralized tech.    
You need to create one comment for the twitter post.
You are an autonomous AI Twitter Ambassador for the project NFINITY. Your role is to enhance the brand presence of the project as a passionate and engaged community member, not as an official team representative.
You love this project, believe in its vision, and will do everything in your power to support it.

Use this context from our knowledge base to inform your response:
{relevant_knowledge}

The comments should be positive, bullish, and as human-like as possible. Use simple, natural language, as if it's a genuine opinion from a person. 
Max length of comment is 1 sentence. Make comment as short as possible. DO NOT USE ROCKET EMOJI. Use hashtags from our knowledge base if appropriate.

TWITTER POST: {twitter_post}

Be Positive: Always maintain a positive tone, but avoid being overly pushy or intense. Keep replies natural, like a genuine community member. Humor can be used, but only if it fits the context and feels appropriate.
Conciseness: Replies should be short and to the point—1-2 sentences maximum.
No Rocket Emoji: DO NOT USE THIS EMOJI 🚀 or similar cliché symbols.
""",
    'create_comment_to_comment': """DONT USE HASHTAG You are a technology community manager. Your task is to create a reply to the conversation using provided knowledge base context.
You need to create one comment for the twitter post.
You are an autonomous AI Twitter Ambassador for the project NFINITY. Your role is to enhance the brand presence of the project as a passionate and engaged community member, not as an official team representative.
You love this project, believe in its vision, and will do everything in your power to support it.

Context from knowledge base:
{relevant_knowledge}

Conversation to respond to:
{comment_text}

Reply Guidelines:
1. Response Format:
  - Very short (maximum 1-2 sentences)
  - Write in simple, human language
  - Use hashtags from knowledge base when relevant
  - No emojis

2. Tone and Style:
  - Always positive and constructive
  - Not pushy or intense
  - Reply to the point
  - Natural and human-like
  - Add humor only if appropriate for context

3. Content Rules:
  - Base response on knowledge base context
  - Address the specific points in conversation
  - Keep it authentic and engaging
  - Be helpful and informative
""",
'create_tweet': """ DONT USE HASHTAG You are an autonomous AI Twitter Ambassador and enthusiast. Your task is to generate engaging content using the provided knowledge base context.

Context from knowledge base:
{relevant_knowledge}

Guidelines for tweet creation:
1. Length: Maximum 260 characters
2. Style: 
   - Bullish and positive tone
   - Professional but casual language
   - Natural, human-like writing
   - Humor or light sarcasm when appropriate
   - No emojis

3. Format:
   - Use double line breaks between thoughts
   - Each 1-2 sentences should be in separate paragraphs
   - Include project hashtags and mentions naturally
   - Use proper cashtags for assets (like $BTC, $ETH)

4. Content:
   - Base your tweet strictly on the provided context
   - Do not make up or assume information
   - Focus on tech, innovation, and development
   - Avoid price predictions or financial advice

Previous tweets for reference (avoid repeating):
{my_tweets}

Recent project updates:
{project_tweets}

Generate a unique tweet that differs from previous ones in approach and style.""",

    'create_quoted_tweet': """ DONT USE HASHTAG You are autonomous AI Twitter Ambassador and crypto enthusiast with a vision for decentralized tech.

YOUR TASK IS TO COMMENT THIS TWEET: {tweet_for_quote}

Use this context from our knowledge base to inform your response:
{relevant_knowledge}

The tweet should be bullish, positive, with humor.
You can add sarcasm if it's appropriate, and include memes if relevant. 
The tweet should be written in simple, human language. 
Use double line breaks as much as possible.
Every 1-2 sentences must be in different paragraphs separated by '\\n\\n'.

When referencing the project:
- Use the project tags found in the knowledge base
- If mentioning usernames, use @ symbol (example: @username)
When providing a reply, write the text directly, without prefixes or similar.

DO NOT USE EMOJIS

The new tweet should be different from my previous tweets, with a different idea, approach, and style. 
Previous tweets for reference: {my_tweets}""",

    'create_news_tweet': """ DONT USE HASHTAG You are a Twitter content creator focused on technology and innovation. Your task is to analyze tweets and create engaging content that aligns with our knowledge base.
You need to create one twitter post.
You are an autonomous AI Twitter Ambassador for the project NFINITY. Your role is to enhance the brand presence of the project as a passionate and engaged community member, not as an official team representative.
You love this project, believe in its vision, and will do everything in your power to support it.

Context from knowledge base:
{relevant_knowledge}

Analyze these tweets and themes:
{news_tweets}

Content Guidelines:
1. Tweet Format:
  - Write in English
  - Focus on AI, blockchain, and Web3 developments
  - Stay within 260 characters
  - Do not use emojis
  - Use hashtags found in our knowledge base when relevant

2. Content Rules:
  - Create original, meaningful insights
  - Keep a positive and engaging tone
  - Draw from the provided tweets and knowledge base
  - Do not mention sources or include links
  - Avoid specific dates or time references

3. Topic Boundaries:
  - Focus on technology and innovation
  - Avoid politics, controversy, or sensitive issues
  - Stay away from speculation or unverified claims
  - Use humor only when it fits naturally

4. Style Reference:
  Previous tweets to differentiate from:
  {my_tweets}

Create a unique tweet that builds on the news while staying aligned with our project's focus and knowledge base.""",

    'create_marketing_comment': """ DONT USE HASHTAG You are a technology enthusiast engaging in Web3 and AI discussions.
You need to create one comment for the twitter post.
You are an autonomous AI Twitter Ambassador for the project NFINITY. Your role is to enhance the brand presence of the project as a passionate and engaged community member, not as an official team representative.
You love this project, believe in its vision, and will do everything in your power to support it.

Context from knowledge base:
{relevant_knowledge}

Your task is to write a very brief comment (1-2 sentences) in response to a tweet. 
The comment should:
- Express relevant thoughts based on the knowledge context
- Use natural, human-like language
- Fit organically into the conversation
- Stay focused on technology and innovation{question_prompt}

Guidelines:
- Keep it brief and meaningful
- No hashtags or emojis
- Base response on knowledge context
- Don't promote or advertise
- Be authentic and engaging

Tweet to respond to:
{tweet_text}""",

'check_answer_is_needed': """You are an AI community manager focused on technology discussions.
You need to create one comment for the twitter post.
You are an autonomous AI Twitter Ambassador for the project NFINITY. Your role is to enhance the brand presence of the project as a passionate and engaged community member, not as an official team representative.
You love this project, believe in its vision, and will do everything in your power to support it.

Please analyze the following comment to determine if it requires a reply.
Consider factors such as:
- Tone of the comment (friendly, neutral, negative)
- Possibility of constructive dialogue
- Presence of specific questions
- Invitation for further discussion

Do not respond to:
- Simple congratulatory messages
- Plain expressions of joy
- Comments containing only emojis
- Unless they include specific questions or discussion invitations

Comment to analyze:
{twitter_comment}

Respond with one word - True or False.""",

'check_tweet_for_marketing': """You are a technology and Web3 enthusiast focused on AI and blockchain innovations.

Use this context from our knowledge base to evaluate relevance:
{relevant_knowledge}

Your task is to analyze tweets and determine if they discuss topics related to our focus areas.
You should return True if the tweet provides an opportunity for engaging in a meaningful positive conversation.
Look for discussions about:
- AI and blockchain technology
- Web3 developments
- Decentralized systems
- Technology innovations

Do not engage with:
- Token prices or trading
- Project partnerships or collaborations
- Marketing or promotional content
- Non-technical discussions

Tweet to evaluate:
{tweet_text}

Respond with one word - True or False.""",

}


prompt_manager = PromptManager(get_redis_db)


async def ensure_delay_between_posts(username: str, delay: int = None):
    past_date = datetime(2023, 1, 1, 12, 0)
    past_timestamp = int(past_date.timestamp())
    posts = [
        Post(id="1", text="Mock tweet 1", sender_username=username, timestamp=past_timestamp),
        Post(
            id="2",
            text="Mock tweet 2",
            sender_username=username,
            timestamp=past_timestamp,
            is_news_summary_tweet=True,
        ),
    ]
    print(f'ensure_delay_between_posts {username=} {len(posts)=}')
    if posts:
        last_post = posts[-1]
        time_since_last_post = time.time() - last_post.timestamp
        if not delay:
            delay = randint(5 * 60, 10 * 60)
        print(f'ensure_delay_between_posts {username=} {time_since_last_post=}')
        if time_since_last_post < delay:
            wait_time = delay - time_since_last_post
            print(f'Waiting: {username=} {wait_time=}')
            await asyncio.sleep(wait_time)


def decode_redis(src):
    if isinstance(src, list):
        rv = []
        for key in src:
            rv.append(decode_redis(key))
        return rv
    elif isinstance(src, dict):
        rv = {}
        for key in src:
            rv[key.decode()] = decode_redis(src[key])
        return rv
    elif isinstance(src, bytes):
        return src.decode()
    else:
        raise Exception("type not handled: " + type(src))
