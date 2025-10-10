"""Tool Execution Cache for performance optimization.
Based on Go SDK ToolCache implementation with Python enhancements.
Thread-safe with TTL support and LRU eviction.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from threading import RLock
from typing import Any, Dict, Optional

from loguru import logger

from .types import CacheEntry, generate_cache_key


class ToolExecutionCache:
    """Thread-safe cache for tool execution results.
    Implements LRU eviction with TTL support, matching Go SDK functionality.
    """

    def __init__(self, max_size: int = 1000, default_ttl_seconds: int = 300):
        """Initialize tool execution cache.

        Args:
            max_size: Maximum number of cache entries
            default_ttl_seconds: Default TTL in seconds (5 minutes)

        """
        self.max_size = max_size
        self.default_ttl_seconds = default_ttl_seconds
        self.entries: dict[str, CacheEntry] = {}
        self.lock = RLock()
        self.stats = {"hits": 0, "misses": 0, "evictions": 0, "sets": 0}

        logger.debug(
            f"Initialized ToolExecutionCache: max_size={max_size}, ttl={default_ttl_seconds}s"
        )

    def get(self, tool_name: str, args: dict[str, Any]) -> Any | None:
        """Get cached result for tool execution.

        Args:
            tool_name: Name of the tool
            args: Tool arguments

        Returns:
            Cached result or None if not found/expired

        """
        cache_key = generate_cache_key(tool_name, args)
        return self.get_by_key(cache_key)

    def get_by_key(self, key: str) -> Any | None:
        """Get cached result by cache key.

        Args:
            key: Cache key

        Returns:
            Cached result or None if not found/expired

        """
        with self.lock:
            entry = self.entries.get(key)

            if entry is None:
                self.stats["misses"] += 1
                return None

            # Check if entry has expired
            if self._is_expired(entry):
                del self.entries[key]
                self.stats["misses"] += 1
                logger.debug(f"Cache entry expired: {key}")
                return None

            # Update access information
            entry.accessed_at = datetime.now()
            entry.access_count += 1

            self.stats["hits"] += 1
            logger.debug(f"Cache hit: {key} (access_count={entry.access_count})")

            return entry.value

    def set(
        self,
        tool_name: str,
        args: dict[str, Any],
        value: Any,
        ttl_seconds: int | None = None,
    ) -> None:
        """Cache tool execution result.

        Args:
            tool_name: Name of the tool
            args: Tool arguments
            value: Result to cache
            ttl_seconds: Custom TTL in seconds (uses default if None)

        """
        cache_key = generate_cache_key(tool_name, args)
        self.set_by_key(cache_key, value, ttl_seconds)

    def set_by_key(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """Cache result by cache key.

        Args:
            key: Cache key
            value: Result to cache
            ttl_seconds: Custom TTL in seconds (uses default if None)

        """
        if ttl_seconds is None:
            ttl_seconds = self.default_ttl_seconds

        with self.lock:
            # Check if we need to evict entries
            if len(self.entries) >= self.max_size:
                self._evict_lru()

            # Create new cache entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=datetime.now(),
                accessed_at=datetime.now(),
                access_count=1,
                ttl_seconds=ttl_seconds,
            )

            self.entries[key] = entry
            self.stats["sets"] += 1

            logger.debug(f"Cached result: {key} (ttl={ttl_seconds}s)")

    def invalidate(self, tool_name: str, args: dict[str, Any]) -> bool:
        """Invalidate cached result for specific tool execution.

        Args:
            tool_name: Name of the tool
            args: Tool arguments

        Returns:
            True if entry was found and removed

        """
        cache_key = generate_cache_key(tool_name, args)
        return self.invalidate_by_key(cache_key)

    def invalidate_by_key(self, key: str) -> bool:
        """Invalidate cached result by cache key.

        Args:
            key: Cache key

        Returns:
            True if entry was found and removed

        """
        with self.lock:
            if key in self.entries:
                del self.entries[key]
                logger.debug(f"Invalidated cache entry: {key}")
                return True
            return False

    def clear(self) -> None:
        """Clear all cache entries."""
        with self.lock:
            entry_count = len(self.entries)
            self.entries.clear()

            # Reset stats
            self.stats = {"hits": 0, "misses": 0, "evictions": 0, "sets": 0}

            logger.info(f"Cleared cache: removed {entry_count} entries")

    def size(self) -> int:
        """Get current cache size."""
        with self.lock:
            return len(self.entries)

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Statistics dictionary

        """
        with self.lock:
            total_requests = self.stats["hits"] + self.stats["misses"]
            hit_rate = (
                self.stats["hits"] / total_requests if total_requests > 0 else 0.0
            )

            return {
                "size": len(self.entries),
                "max_size": self.max_size,
                "hits": self.stats["hits"],
                "misses": self.stats["misses"],
                "hit_rate": round(hit_rate, 3),
                "evictions": self.stats["evictions"],
                "sets": self.stats["sets"],
                "default_ttl_seconds": self.default_ttl_seconds,
            }

    def cleanup_expired(self) -> int:
        """Remove all expired entries.

        Returns:
            Number of entries removed

        """
        with self.lock:
            expired_keys = []

            for key, entry in self.entries.items():
                if self._is_expired(entry):
                    expired_keys.append(key)

            for key in expired_keys:
                del self.entries[key]

            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

            return len(expired_keys)

    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if cache entry has expired.

        Args:
            entry: Cache entry to check

        Returns:
            True if expired

        """
        expiry_time = entry.created_at + timedelta(seconds=entry.ttl_seconds)
        return datetime.now() > expiry_time

    def _evict_lru(self) -> None:
        """Evict least recently used entry.
        Implements LRU eviction strategy matching Go SDK.
        """
        if not self.entries:
            return

        # Find entry with oldest access time
        oldest_key = None
        oldest_time = None

        for key, entry in self.entries.items():
            if oldest_key is None or entry.accessed_at < oldest_time:
                oldest_key = key
                oldest_time = entry.accessed_at

        # Remove oldest entry
        if oldest_key is not None:
            del self.entries[oldest_key]
            self.stats["evictions"] += 1
            logger.debug(f"Evicted LRU cache entry: {oldest_key}")

    async def start_cleanup_task(self, cleanup_interval_seconds: int = 60) -> None:
        """Start background task to periodically clean up expired entries.

        Args:
            cleanup_interval_seconds: Cleanup interval in seconds

        """

        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(cleanup_interval_seconds)
                    self.cleanup_expired()
                except asyncio.CancelledError:
                    logger.debug("Cache cleanup task cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in cache cleanup task: {e}")

        asyncio.create_task(cleanup_loop())
        logger.info(f"Started cache cleanup task: interval={cleanup_interval_seconds}s")


class CacheKeyBuilder:
    """Utility class for building cache keys with advanced features."""

    @staticmethod
    def build_key(
        tool_name: str,
        args: dict[str, Any],
        include_user: bool = False,
        user_id: str | None = None,
    ) -> str:
        """Build cache key with optional user isolation.

        Args:
            tool_name: Name of the tool
            args: Tool arguments
            include_user: Whether to include user in cache key
            user_id: User ID for isolation

        Returns:
            Cache key string

        """
        base_key = generate_cache_key(tool_name, args)

        if include_user and user_id:
            return f"user:{user_id}:{base_key}"

        return base_key

    @staticmethod
    def build_pattern_key(pattern: str, **kwargs) -> str:
        """Build cache key from pattern with variable substitution.

        Args:
            pattern: Pattern string with {variable} placeholders
            **kwargs: Variables to substitute

        Returns:
            Cache key string

        """
        try:
            return pattern.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Missing variable in cache key pattern: {e}")
            return pattern

    @staticmethod
    def extract_tool_from_key(key: str) -> str | None:
        """Extract tool name from cache key.

        Args:
            key: Cache key

        Returns:
            Tool name or None if not extractable

        """
        # Handle user-prefixed keys
        if key.startswith("user:"):
            parts = key.split(":", 2)
            if len(parts) >= 3:
                key = parts[2]

        # Extract tool name (everything before first colon)
        if ":" in key:
            return key.split(":", 1)[0]

        return key
