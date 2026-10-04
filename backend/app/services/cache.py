"""
VARUNA Cache Abstraction Layer.
SIH 2026 Problem Statement: SIH26081

Provides high-performance caching for computationally intensive operations:
1. Spatial Model Weight Maps (GeoJSON generation)
2. Latest Multi-Model Forecast Fusions
3. Model Skill Scores & Context Vectors
4. Benchmark Summary Metrics

Architecture:
- Abstract CacheProvider interface swappable with Redis/Memcached in enterprise deployments
- Thread-safe InMemoryCacheProvider with TTL expiration and LRU capacity bounds

Cache Invalidation Rules:
- 'forecast:*': Invalidate upon new forecast cycle ingestion (TTL: 60s)
- 'weight_map:*': Invalidate upon failure injection or skill recalibration (TTL: 300s)
- 'skill:*': Invalidate upon verification feedback cycle (TTL: 300s)
- 'benchmark:*': Invalidate upon new experiment run (TTL: 600s)
"""

import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from threading import Lock
import logging

logger = logging.getLogger("varuna-cache")


class CacheProvider(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl_seconds: int = 300):
        pass

    @abstractmethod
    def delete(self, key: str):
        pass

    @abstractmethod
    def clear_prefix(self, prefix: str):
        pass


class InMemoryCacheProvider(CacheProvider):
    """Thread-safe in-memory cache with TTL support."""

    def __init__(self, max_keys: int = 1000):
        self._store: Dict[str, Any] = {}
        self._expiry: Dict[str, float] = {}
        self._max_keys = max_keys
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._store:
                return None
            if time.time() > self._expiry.get(key, 0.0):
                # Expired
                del self._store[key]
                if key in self._expiry:
                    del self._expiry[key]
                return None
            return self._store[key]

    def set(self, key: str, value: Any, ttl_seconds: int = 300):
        with self._lock:
            # Enforce max key capacity
            if len(self._store) >= self._max_keys and key not in self._store:
                # Evict oldest entry
                oldest_key = min(self._expiry, key=self._expiry.get)
                self._store.pop(oldest_key, None)
                self._expiry.pop(oldest_key, None)

            self._store[key] = value
            self._expiry[key] = time.time() + ttl_seconds

    def delete(self, key: str):
        with self._lock:
            self._store.pop(key, None)
            self._expiry.pop(key, None)

    def clear_prefix(self, prefix: str):
        with self._lock:
            matching = [k for k in self._store.keys() if k.startswith(prefix)]
            for k in matching:
                del self._store[k]
                self._expiry.pop(k, None)

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            active = sum(1 for k, exp in self._expiry.items() if time.time() <= exp)
            return {
                "total_cached_keys": len(self._store),
                "active_valid_keys": active,
                "max_capacity": self._max_keys
            }


cache_service = InMemoryCacheProvider()
