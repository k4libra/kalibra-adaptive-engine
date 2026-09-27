import asyncio
import contextlib
from collections.abc import AsyncGenerator, Awaitable, Callable, Sequence
from contextlib import AbstractAsyncContextManager, AsyncExitStack, asynccontextmanager
from typing import TypedDict

import httpx
from fastapi import FastAPI
from redis.asyncio import Redis

from kalibra_engine.shared.infrastructure.http_client import create_http_client
from kalibra_engine.shared.infrastructure.redis_client import create_redis_client
from kalibra_engine.shared.infrastructure.settings import Settings, get_settings
from kalibra_engine.shared.interfaces.messaging.redis_task_worker import (
    ProblemMapper,
    RedisTaskWorker,
)
from kalibra_engine.shared.interfaces.messaging.task_handler import TaskHandler

TaskHandlersFactory = Callable[[httpx.AsyncClient, Settings], Awaitable[Sequence[TaskHandler]]]
Lifespan = Callable[[FastAPI], AbstractAsyncContextManager["EngineState"]]


class EngineState(TypedDict):
    """Objects opened at startup and exposed to requests through ``request.state``."""

    http_client: httpx.AsyncClient
    redis: "Redis | None"


def build_lifespan(task_handlers: TaskHandlersFactory, problem_for: ProblemMapper) -> Lifespan:
    """Build the application lifespan.

    Always opens the shared outbound HTTP client. When ``REDIS_ENABLED`` is true it also
    opens the Redis client and runs the task worker in the background until shutdown.

    Args:
        task_handlers: Builds the queue handlers once the HTTP client exists.
        problem_for: Maps exceptions to problem details for failed tasks.

    Returns:
        The lifespan context manager factory for ``FastAPI(lifespan=...)``.
    """

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[EngineState]:
        settings = get_settings()
        async with create_http_client(settings) as http_client, AsyncExitStack() as stack:
            redis = None
            if settings.redis_enabled:
                redis = create_redis_client(settings)
                stack.push_async_callback(redis.aclose)
                worker = RedisTaskWorker(
                    redis, settings, await task_handlers(http_client, settings), problem_for
                )
                worker_task = asyncio.create_task(worker.run(), name="redis-task-worker")
                stack.push_async_callback(_stop, worker_task)
            yield {"http_client": http_client, "redis": redis}

    return lifespan


async def _stop(task: asyncio.Task[None]) -> None:
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
