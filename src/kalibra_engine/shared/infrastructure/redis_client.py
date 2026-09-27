from redis.asyncio import Redis

from kalibra_engine.shared.infrastructure.settings import Settings


def create_redis_client(settings: Settings) -> "Redis":
    """Build the Redis client used by the task worker and the readiness probe.

    Args:
        settings: Engine settings with the Redis URL.

    Returns:
        A pooled asyncio client that decodes responses to ``str``; the caller closes it.
    """
    return Redis.from_url(settings.redis_url.get_secret_value(), decode_responses=True)
