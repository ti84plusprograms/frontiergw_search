from redis import Redis

from app.core.config import settings


def get_redis() -> Redis:
    return Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=settings.redis_connect_timeout_seconds,
        socket_timeout=settings.redis_connect_timeout_seconds,
        health_check_interval=30,
    )
