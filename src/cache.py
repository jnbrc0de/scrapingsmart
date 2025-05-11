import redis
from typing import Any, Optional, Dict
import json
import hashlib
from datetime import datetime
import logging
from config.cache_config import (
    REDIS_CONFIG,
    CACHE_TTL,
    CACHE_PATTERNS,
    CACHE_LAYERS
)

logger = logging.getLogger(__name__)

class MultiLayerCache:
    def __init__(self):
        self.memory_cache: Dict[str, Any] = {}
        self.redis_client = redis.Redis.from_url(
            REDIS_CONFIG['url'],
            max_connections=REDIS_CONFIG['max_connections'],
            socket_timeout=REDIS_CONFIG['timeout'],
            retry_on_timeout=REDIS_CONFIG['retry_on_timeout']
        )

    def _generate_key(self, pattern: str, **kwargs) -> str:
        """Generate cache key using pattern and parameters."""
        return pattern.format(**kwargs)

    def _hash_fingerprint(self, fingerprint: Dict[str, Any]) -> str:
        """Generate hash for fingerprint data."""
        return hashlib.md5(json.dumps(fingerprint, sort_keys=True).encode()).hexdigest()

    def get_strategy(self, domain: str, strategy_type: str) -> Optional[Dict[str, Any]]:
        """Get strategy from cache."""
        key = self._generate_key(CACHE_PATTERNS['strategy'], domain=domain, type=strategy_type)
        
        # Try memory cache first
        if CACHE_LAYERS['memory']['enabled']:
            if key in self.memory_cache:
                return self.memory_cache[key]
        
        # Try Redis cache
        if CACHE_LAYERS['redis']['enabled']:
            try:
                data = self.redis_client.get(key)
                if data:
                    strategy = json.loads(data)
                    # Update memory cache
                    if CACHE_LAYERS['memory']['enabled']:
                        self.memory_cache[key] = strategy
                    return strategy
            except redis.RedisError as e:
                logger.error(f"Redis error: {e}")
        
        return None

    def set_strategy(self, domain: str, strategy_type: str, strategy: Dict[str, Any]) -> None:
        """Cache strategy data."""
        key = self._generate_key(CACHE_PATTERNS['strategy'], domain=domain, type=strategy_type)
        
        # Update memory cache
        if CACHE_LAYERS['memory']['enabled']:
            self.memory_cache[key] = strategy
        
        # Update Redis cache
        if CACHE_LAYERS['redis']['enabled']:
            try:
                self.redis_client.setex(
                    key,
                    CACHE_TTL['strategy'],
                    json.dumps(strategy)
                )
            except redis.RedisError as e:
                logger.error(f"Redis error: {e}")

    def get_fingerprint(self, domain: str, fingerprint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get fingerprint from cache."""
        fingerprint_hash = self._hash_fingerprint(fingerprint)
        key = self._generate_key(CACHE_PATTERNS['fingerprint'], domain=domain, hash=fingerprint_hash)
        
        # Try memory cache first
        if CACHE_LAYERS['memory']['enabled']:
            if key in self.memory_cache:
                return self.memory_cache[key]
        
        # Try Redis cache
        if CACHE_LAYERS['redis']['enabled']:
            try:
                data = self.redis_client.get(key)
                if data:
                    cached_fingerprint = json.loads(data)
                    # Update memory cache
                    if CACHE_LAYERS['memory']['enabled']:
                        self.memory_cache[key] = cached_fingerprint
                    return cached_fingerprint
            except redis.RedisError as e:
                logger.error(f"Redis error: {e}")
        
        return None

    def set_fingerprint(self, domain: str, fingerprint: Dict[str, Any]) -> None:
        """Cache fingerprint data."""
        fingerprint_hash = self._hash_fingerprint(fingerprint)
        key = self._generate_key(CACHE_PATTERNS['fingerprint'], domain=domain, hash=fingerprint_hash)
        
        # Update memory cache
        if CACHE_LAYERS['memory']['enabled']:
            self.memory_cache[key] = fingerprint
        
        # Update Redis cache
        if CACHE_LAYERS['redis']['enabled']:
            try:
                self.redis_client.setex(
                    key,
                    CACHE_TTL['fingerprint'],
                    json.dumps(fingerprint)
                )
            except redis.RedisError as e:
                logger.error(f"Redis error: {e}")

    def clear_expired(self) -> None:
        """Clear expired entries from memory cache."""
        if CACHE_LAYERS['memory']['enabled']:
            current_time = datetime.now().timestamp()
            expired_keys = [
                key for key, (_, timestamp) in self.memory_cache.items()
                if current_time - timestamp > CACHE_LAYERS['memory']['ttl']
            ]
            for key in expired_keys:
                del self.memory_cache[key] 