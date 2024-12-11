# fmt: off
import json
import logging
import os
import time
from datetime import datetime
from typing import Any, List, Optional, Union
from enum import Enum

import redis


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


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

# Initialize a default instance
db = RedisDB()
