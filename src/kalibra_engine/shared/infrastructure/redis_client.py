from redis.asyncio import Redis

from kalibra_engine.shared.infrastructure.settings import Settings

_SOCKET_TIMEOUT_MARGIN_SECONDS = 5.0


def create_redis_client(settings: Settings) -> "Redis":
    """Build the Redis client used by the task worker and the readiness probe.

    Args:
        settings: Engine settings with the Redis URL.

    Returns:
        A pooled asyncio client that decodes responses to ``str``; the caller closes it.
        Its socket timeout outlasts the worker's blocking read, so an idle stream is an
        empty read and not a timeout.
    """
    return Redis.from_url(
        settings.redis_url.get_secret_value(),
        decode_responses=True,
        socket_timeout=settings.redis_block_milliseconds / 1000 + _SOCKET_TIMEOUT_MARGIN_SECONDS,
    )
