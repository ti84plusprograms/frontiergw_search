"""Fail-open Redis cache, lock, invalidation, and atomic counter service."""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any

from redis import Redis

from app.core.cache_keys import safe_key_id
from app.core.config import settings
from app.core.metrics import CACHE_ERRORS, CACHE_HITS, CACHE_MISSES, REDIS_DURATION, REDIS_FAILURES
from app.core.observability import log_event
from app.db.redis import get_redis


@dataclass(frozen=True, slots=True)
class CacheRead:
    value: dict[str, Any] | list[Any] | None
    outcome: str


@dataclass(frozen=True, slots=True)
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    retry_after: int
    enforced: bool


class CacheService:
    def __init__(self, client: Redis | None = None, *, enabled: bool | None = None) -> None:
        self.client = client or get_redis()
        self.enabled = settings.cache_enabled if enabled is None else enabled
        self._disabled_until = 0.0

    def _available(self) -> bool:
        return self.enabled and time.monotonic() >= self._disabled_until

    def _failed(self, operation: str, exc: Exception) -> None:
        self._disabled_until = time.monotonic() + settings.cache_error_backoff_seconds
        CACHE_ERRORS.labels(operation=operation).inc()
        REDIS_FAILURES.labels(operation=operation).inc()
        log_event(
            "redis.connection_failed",
            level=logging.WARNING,
            failure_category=type(exc).__name__,
        )

    def get_json(self, key: str, *, namespace: str) -> CacheRead:
        if not self._available():
            return CacheRead(None, "BYPASS")
        started = time.perf_counter()
        try:
            raw = self.client.get(key)
            if raw is None:
                CACHE_MISSES.labels(namespace=namespace).inc()
                log_event("cache.miss", cache_status="MISS", cache_key_id=safe_key_id(key))
                return CacheRead(None, "MISS")
            try:
                value = json.loads(raw)
            except (TypeError, ValueError) as exc:
                CACHE_ERRORS.labels(operation="decode").inc()
                log_event(
                    "cache.error",
                    level=logging.WARNING,
                    cache_status="CORRUPT",
                    cache_key_id=safe_key_id(key),
                    failure_category=type(exc).__name__,
                )
                self.delete(key)
                return CacheRead(None, "CORRUPT")
            if not isinstance(value, (dict, list)):
                self.delete(key)
                return CacheRead(None, "CORRUPT")
            CACHE_HITS.labels(namespace=namespace).inc()
            log_event("cache.hit", cache_status="HIT", cache_key_id=safe_key_id(key))
            return CacheRead(value, "HIT")
        except Exception as exc:
            self._failed("get", exc)
            return CacheRead(None, "ERROR")
        finally:
            REDIS_DURATION.labels(operation="get").observe(time.perf_counter() - started)

    def set_json(self, key: str, value: dict[str, Any] | list[Any], ttl_seconds: int) -> bool:
        if not self._available():
            return False
        started = time.perf_counter()
        try:
            self.client.set(
                key, json.dumps(value, sort_keys=True, separators=(",", ":")), ex=ttl_seconds
            )
            return True
        except Exception as exc:
            self._failed("set", exc)
            return False
        finally:
            REDIS_DURATION.labels(operation="set").observe(time.perf_counter() - started)

    def delete(self, key: str) -> bool:
        if not self._available():
            return False
        try:
            self.client.delete(key)
            return True
        except Exception as exc:
            self._failed("delete", exc)
            return False

    def invalidate_prefix(self, prefix: str, *, max_keys: int = 1000) -> int:
        """Best-effort bounded invalidation; versioned search keys remain the primary guard."""
        if not self._available():
            return 0
        deleted = 0
        try:
            for key in self.client.scan_iter(match=f"{prefix}*", count=100):
                if deleted >= max_keys:
                    break
                deleted += int(self.client.delete(key))
            return deleted
        except Exception as exc:
            self._failed("invalidate", exc)
            return deleted

    def acquire_lock(self, key: str) -> str | None:
        if not self._available():
            return None
        token = uuid.uuid4().hex
        try:
            acquired = self.client.set(
                f"lock:{key}", token, nx=True, ex=settings.cache_lock_ttl_seconds
            )
            return token if acquired else None
        except Exception as exc:
            self._failed("lock", exc)
            return None

    def release_lock(self, key: str, token: str | None) -> None:
        if not token or not self._available():
            return
        script = (
            "if redis.call('get', KEYS[1]) == ARGV[1] then "
            "return redis.call('del', KEYS[1]) else return 0 end"
        )
        try:
            self.client.eval(script, 1, f"lock:{key}", token)
        except Exception as exc:
            self._failed("unlock", exc)

    def rate_limit(self, key: str, limit: int, window_seconds: int = 60) -> RateLimitResult:
        # Cache enablement and limiter enablement are independent. A Redis error
        # still opens both features for the bounded backoff window.
        if not settings.rate_limit_enabled or time.monotonic() < self._disabled_until:
            return RateLimitResult(True, limit, limit, 0, False)
        script = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
local ttl = redis.call('TTL', KEYS[1])
return {count, ttl}
"""
        started = time.perf_counter()
        try:
            count, ttl = self.client.eval(script, 1, key, window_seconds)
            current = int(count)
            retry_after = max(1, int(ttl))
            return RateLimitResult(
                allowed=current <= limit,
                limit=limit,
                remaining=max(0, limit - current),
                retry_after=retry_after,
                enforced=True,
            )
        except Exception as exc:
            self._failed("rate_limit", exc)
            return RateLimitResult(True, limit, limit, 0, False)
        finally:
            REDIS_DURATION.labels(operation="rate_limit").observe(time.perf_counter() - started)


_cache_service: CacheService | None = None


def get_cache_service() -> CacheService:
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service


def reset_cache_service() -> None:
    global _cache_service
    _cache_service = None
