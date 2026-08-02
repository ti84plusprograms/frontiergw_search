from functools import lru_cache

from redis import Redis

from app.core.config import settings


@lru_cache(maxsize=1)
def get_redis() -> Redis:
    timeout = settings.cache_operation_timeout_ms / 1000
    return Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=timeout,
        socket_timeout=timeout,
        health_check_interval=30,
        retry_on_timeout=False,
        decode_responses=True,
    )
