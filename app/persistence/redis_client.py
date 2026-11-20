
import redis

from app.config import get_settings


def get_redis_client() -> redis.Redis:
    settings = get_settings()

    return redis.Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )


def check_redis_connection() -> bool:
    client = get_redis_client()

    try:
        return bool(client.ping())
    finally:
        client.close()
