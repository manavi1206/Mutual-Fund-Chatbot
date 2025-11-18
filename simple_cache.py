"""
Simple In-Memory Cache with Redis Support
Replaces enhanced_cache for simpler use case with optional Redis backend
"""
from typing import Optional, Any, Dict
from datetime import datetime, timedelta
import hashlib
import json
import pickle


class SimpleCache:
    """Simple cache with in-memory and optional Redis backend"""
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600, 
                 use_redis: bool = False, redis_host: str = "localhost",
                 redis_port: int = 6379, redis_db: int = 1):
        """
        Initialize simple cache
        
        Args:
            max_size: Maximum number of items to cache in memory
            ttl_seconds: Time-to-live in seconds
            use_redis: Whether to use Redis as backend
            redis_host: Redis host
            redis_port: Redis port
            redis_db: Redis database number
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.use_redis = use_redis
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_order = []  # For LRU eviction
        
        # Initialize Redis if enabled
        self.redis_client = None
        if use_redis:
            try:
                import redis
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    decode_responses=False  # Store binary data
                )
                # Test connection
                self.redis_client.ping()
                print("✓ Redis connected for cache backend")
            except ImportError:
                print("⚠️  Redis not installed. Install with: pip install redis")
                print("   Falling back to in-memory cache only")
                self.use_redis = False
            except Exception as e:
                print(f"⚠️  Redis connection failed: {e}")
                print("   Falling back to in-memory cache only")
                self.use_redis = False
    
    def _get_cache_key(self, key: str) -> str:
        """Generate cache key hash"""
        return hashlib.md5(key.encode()).hexdigest()
    
    def _is_expired(self, item: Dict[str, Any]) -> bool:
        """Check if cache item is expired"""
        if 'expires_at' not in item:
            return True
        return datetime.now() > item['expires_at']
    
    def _evict_lru(self):
        """Evict least recently used item"""
        if len(self._cache) >= self.max_size and self._access_order:
            lru_key = self._access_order.pop(0)
            if lru_key in self._cache:
                del self._cache[lru_key]
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for Redis storage"""
        try:
            return pickle.dumps(value)
        except Exception:
            # Fallback to JSON for simple types
            return json.dumps(value).encode('utf-8')
    
    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize value from Redis"""
        try:
            return pickle.loads(data)
        except Exception:
            # Fallback to JSON
            return json.loads(data.decode('utf-8'))
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache (checks Redis first, then memory)
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        cache_key = self._get_cache_key(key)
        
        # Try Redis first if enabled
        if self.use_redis and self.redis_client:
            try:
                data = self.redis_client.get(cache_key)
                if data:
                    value = self._deserialize_value(data)
                    # Update memory cache for faster access
                    self._cache[cache_key] = {
                        'value': value,
                        'expires_at': datetime.now() + timedelta(seconds=self.ttl_seconds),
                        'created_at': datetime.now()
                    }
                    if cache_key not in self._access_order:
                        self._access_order.append(cache_key)
                    return value
            except Exception as e:
                # Redis failed, fall back to memory
                pass
        
        # Check memory cache
        if cache_key not in self._cache:
            return None
        
        item = self._cache[cache_key]
        
        # Check if expired
        if self._is_expired(item):
            del self._cache[cache_key]
            if cache_key in self._access_order:
                self._access_order.remove(cache_key)
            # Also remove from Redis if enabled
            if self.use_redis and self.redis_client:
                try:
                    self.redis_client.delete(cache_key)
                except Exception:
                    pass
            return None
        
        # Update access order (move to end)
        if cache_key in self._access_order:
            self._access_order.remove(cache_key)
        self._access_order.append(cache_key)
        
        return item.get('value')
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache (stores in both Redis and memory)
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        cache_key = self._get_cache_key(key)
        ttl = ttl or self.ttl_seconds
        
        # Store in Redis if enabled
        if self.use_redis and self.redis_client:
            try:
                serialized = self._serialize_value(value)
                self.redis_client.setex(cache_key, ttl, serialized)
            except Exception as e:
                # Redis failed, continue with memory only
                pass
        
        # Evict from memory if needed
        if cache_key not in self._cache and len(self._cache) >= self.max_size:
            self._evict_lru()
        
        # Store in memory
        self._cache[cache_key] = {
            'value': value,
            'expires_at': datetime.now() + timedelta(seconds=ttl),
            'created_at': datetime.now()
        }
        
        # Update access order
        if cache_key in self._access_order:
            self._access_order.remove(cache_key)
        self._access_order.append(cache_key)
    
    def clear(self) -> None:
        """Clear all cache (both Redis and memory)"""
        self._cache.clear()
        self._access_order.clear()
        
        if self.use_redis and self.redis_client:
            try:
                # Clear all keys (be careful in production!)
                # For now, just clear current database
                self.redis_client.flushdb()
            except Exception:
                pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        # Remove expired items from memory
        expired = [k for k, v in self._cache.items() if self._is_expired(v)]
        for k in expired:
            del self._cache[k]
            if k in self._access_order:
                self._access_order.remove(k)
        
        stats = {
            'size': len(self._cache),
            'max_size': self.max_size,
            'ttl_seconds': self.ttl_seconds,
            'redis_enabled': self.use_redis,
            'redis_connected': self.use_redis and self.redis_client is not None
        }
        
        # Add Redis stats if available
        if self.use_redis and self.redis_client:
            try:
                info = self.redis_client.info('memory')
                stats['redis_memory_used'] = info.get('used_memory_human', 'N/A')
                stats['redis_keys'] = self.redis_client.dbsize()
            except Exception:
                pass
        
        return stats
