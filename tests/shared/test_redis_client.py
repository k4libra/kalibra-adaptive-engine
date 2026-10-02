from kalibra_engine.shared.infrastructure.redis_client import create_redis_client
from kalibra_engine.shared.infrastructure.settings import Settings


def test_socket_timeout_outlasts_the_blocking_read() -> None:
    settings = Settings(_env_file=None, redis_block_milliseconds=5000)

    client = create_redis_client(settings)

    socket_timeout = client.connection_pool.connection_kwargs["socket_timeout"]
    assert socket_timeout > settings.redis_block_milliseconds / 1000
    assert client.connection_pool.connection_kwargs["decode_responses"] is True
