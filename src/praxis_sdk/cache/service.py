"""
Cache Service Implementation

Provides caching functionality, statistics, and management operations
for the Praxis Python SDK.
"""

import time
from datetime import datetime
from typing import Any, Dict, Optional
from collections import defaultdict
import weakref
import gc
from loguru import logger


class CacheService:
    """
    Cache service for Praxis SDK.
    
    Provides in-memory caching with statistics tracking,
    TTL support, and management operations.
    """
    
    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.stats = {
            "created_at": datetime.now().isoformat(),
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "clears": 0,
            "expired": 0,
            "memory_usage_bytes": 0,
            "last_clear": None,
            "categories": defaultdict(int)
        }
        
    def get(self, key: str, category: str = "general") -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            category: Cache category for organization
            
        Returns:
            Cached value or None if not found/expired
        """
        full_key = f"{category}:{key}"
        
        if full_key not in self.cache:
            self.stats["misses"] += 1
            return None
        
        entry = self.cache[full_key]
        
        # Check TTL
        if entry.get("ttl") and time.time() > entry["ttl"]:
            self.delete(key, category)
            self.stats["expired"] += 1
            self.stats["misses"] += 1
            return None
        
        # Update access time
        entry["accessed_at"] = datetime.now().isoformat()
        entry["access_count"] += 1
        
        self.stats["hits"] += 1
        return entry["value"]
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None, 
            category: str = "general") -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live in seconds (optional)
            category: Cache category for organization
            
        Returns:
            True if set successfully
        """
        full_key = f"{category}:{key}"
        
        try:
            entry = {
                "value": value,
                "created_at": datetime.now().isoformat(),
                "accessed_at": datetime.now().isoformat(),
                "access_count": 0,
                "category": category,
                "ttl": time.time() + ttl_seconds if ttl_seconds else None,
                "size_estimate": self._estimate_size(value)
            }
            
            self.cache[full_key] = entry
            self.stats["sets"] += 1
            self.stats["categories"][category] += 1
            self._update_memory_usage()
            
            logger.debug(f"Cached item: {full_key} (category: {category})")
            return True
            
        except Exception as e:
            logger.error(f"Error setting cache item {full_key}: {e}")
            return False
    
    def delete(self, key: str, category: str = "general") -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
            category: Cache category
            
        Returns:
            True if deleted, False if not found
        """
        full_key = f"{category}:{key}"
        
        if full_key in self.cache:
            entry = self.cache[full_key]
            del self.cache[full_key]
            
            self.stats["deletes"] += 1
            self.stats["categories"][entry["category"]] -= 1
            if self.stats["categories"][entry["category"]] <= 0:
                del self.stats["categories"][entry["category"]]
            
            self._update_memory_usage()
            logger.debug(f"Deleted cache item: {full_key}")
            return True
        
        return False
    
    def clear(self, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Clear cache entries.
        
        Args:
            category: Optional category to clear (clears all if None)
            
        Returns:
            Dictionary with clear operation results
        """
        try:
            if category:
                # Clear specific category
                keys_to_delete = [
                    key for key in self.cache.keys() 
                    if key.startswith(f"{category}:")
                ]
                
                deleted_count = 0
                for key in keys_to_delete:
                    if key in self.cache:
                        del self.cache[key]
                        deleted_count += 1
                
                if category in self.stats["categories"]:
                    del self.stats["categories"][category]
                
                result = {
                    "success": True,
                    "category": category,
                    "deleted_count": deleted_count,
                    "timestamp": datetime.now().isoformat()
                }
                
                logger.info(f"Cleared cache category '{category}': {deleted_count} items")
            
            else:
                # Clear all cache
                total_items = len(self.cache)
                self.cache.clear()
                self.stats["categories"].clear()
                
                result = {
                    "success": True,
                    "category": "all",
                    "deleted_count": total_items,
                    "timestamp": datetime.now().isoformat()
                }
                
                logger.info(f"Cleared entire cache: {total_items} items")
            
            self.stats["clears"] += 1
            self.stats["last_clear"] = result["timestamp"]
            self._update_memory_usage()
            
            return result
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        # Calculate additional metrics
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0.0
        miss_rate = (self.stats["misses"] / total_requests * 100) if total_requests > 0 else 0.0
        
        # Get current cache info
        current_items = len(self.cache)
        categories = dict(self.stats["categories"])
        
        # Calculate memory usage
        self._update_memory_usage()
        
        # Find most accessed items
        most_accessed = []
        if self.cache:
            sorted_items = sorted(
                [(key, entry["access_count"]) for key, entry in self.cache.items()],
                key=lambda x: x[1],
                reverse=True
            )
            most_accessed = sorted_items[:10]
        
        return {
            "cache_info": {
                "total_items": current_items,
                "categories": categories,
                "memory_usage_bytes": self.stats["memory_usage_bytes"],
                "memory_usage_mb": round(self.stats["memory_usage_bytes"] / (1024 * 1024), 2)
            },
            "operations": {
                "hits": self.stats["hits"],
                "misses": self.stats["misses"],
                "sets": self.stats["sets"],
                "deletes": self.stats["deletes"],
                "clears": self.stats["clears"],
                "expired": self.stats["expired"]
            },
            "metrics": {
                "hit_rate_percent": round(hit_rate, 2),
                "miss_rate_percent": round(miss_rate, 2),
                "total_requests": total_requests
            },
            "timestamps": {
                "created_at": self.stats["created_at"],
                "last_clear": self.stats["last_clear"],
                "current_time": datetime.now().isoformat()
            },
            "top_accessed": [{"key": key, "access_count": count} for key, count in most_accessed]
        }
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired cache entries.
        
        Returns:
            Number of expired entries removed
        """
        current_time = time.time()
        expired_keys = []
        
        for key, entry in self.cache.items():
            if entry.get("ttl") and current_time > entry["ttl"]:
                expired_keys.append(key)
        
        removed_count = 0
        for key in expired_keys:
            if key in self.cache:
                entry = self.cache[key]
                del self.cache[key]
                
                # Update category count
                category = entry["category"]
                self.stats["categories"][category] -= 1
                if self.stats["categories"][category] <= 0:
                    del self.stats["categories"][category]
                
                removed_count += 1
        
        if removed_count > 0:
            self.stats["expired"] += removed_count
            self._update_memory_usage()
            logger.debug(f"Cleaned up {removed_count} expired cache entries")
        
        return removed_count
    
    def get_category_stats(self, category: str) -> Dict[str, Any]:
        """
        Get statistics for a specific category.
        
        Args:
            category: Cache category
            
        Returns:
            Category-specific statistics
        """
        category_items = {
            key: entry for key, entry in self.cache.items()
            if key.startswith(f"{category}:")
        }
        
        if not category_items:
            return {
                "category": category,
                "total_items": 0,
                "total_size_bytes": 0,
                "items": []
            }
        
        total_size = sum(entry.get("size_estimate", 0) for entry in category_items.values())
        
        items_info = []
        for key, entry in category_items.items():
            items_info.append({
                "key": key.split(":", 1)[1],  # Remove category prefix
                "created_at": entry["created_at"],
                "accessed_at": entry["accessed_at"],
                "access_count": entry["access_count"],
                "size_estimate": entry.get("size_estimate", 0),
                "has_ttl": entry.get("ttl") is not None,
                "expired": entry.get("ttl") and time.time() > entry["ttl"] if entry.get("ttl") else False
            })
        
        return {
            "category": category,
            "total_items": len(category_items),
            "total_size_bytes": total_size,
            "items": items_info
        }
    
    def _estimate_size(self, obj: Any) -> int:
        """Estimate memory size of an object in bytes."""
        try:
            # Simple size estimation
            if isinstance(obj, str):
                return len(obj.encode('utf-8'))
            elif isinstance(obj, (int, float)):
                return 8
            elif isinstance(obj, bool):
                return 1
            elif isinstance(obj, (list, tuple)):
                return sum(self._estimate_size(item) for item in obj) + 8 * len(obj)
            elif isinstance(obj, dict):
                return sum(
                    self._estimate_size(k) + self._estimate_size(v)
                    for k, v in obj.items()
                ) + 8 * len(obj)
            else:
                # Fallback to sys.getsizeof equivalent estimation
                return len(str(obj)) * 2  # Rough estimate
        except Exception:
            return 0
    
    def _update_memory_usage(self):
        """Update memory usage statistics."""
        try:
            total_size = sum(
                entry.get("size_estimate", 0) + 200  # Add overhead per entry
                for entry in self.cache.values()
            )
            self.stats["memory_usage_bytes"] = total_size
        except Exception as e:
            logger.debug(f"Error updating memory usage: {e}")


# Global cache service instance
cache_service = CacheService()