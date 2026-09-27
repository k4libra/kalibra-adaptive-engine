import asyncio
import contextlib
import json
import logging
from collections.abc import Callable, Mapping, Sequence
from http import HTTPStatus
from typing import Any

from pydantic import ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError, ResponseError

from kalibra_engine.shared.infrastructure.settings import Settings
from kalibra_engine.shared.interfaces.messaging.task_envelope import TaskEnvelope
from kalibra_engine.shared.interfaces.messaging.task_handler import TaskHandler
from kalibra_engine.shared.interfaces.messaging.task_result import TaskResult
from kalibra_engine.shared.interfaces.rest.engine_exception_handler import problem_details

logger = logging.getLogger(__name__)

ProblemMapper = Callable[[Exception, str], dict[str, Any]]
StreamEntry = tuple[str, dict[str, str]]

_UNPROCESSABLE = HTTPStatus.UNPROCESSABLE_CONTENT.value
_RECONNECT_BACKOFF_SECONDS = (1, 2, 5, 10, 30)


class RedisTaskWorker:
    """Consume tasks from a Redis stream through a consumer group and publish results.

    Delivery is at least once: a task is acknowledged only after its result is published,
    so a crash leaves it pending and another consumer reclaims it once idle. kalibra-api
    must therefore treat results idempotently by ``taskId``. While a task runs, its
    pending entry is refreshed so long generations are not reclaimed by mistake. Tasks
    delivered more than ``redis_max_deliveries`` times are failed instead of retried.

    Args:
        redis: Client with ``decode_responses=True``.
        settings: Engine settings with the Redis configuration.
        handlers: One handler per task type.
        problem_for: Maps an exception to problem details (shared with REST).
    """

    def __init__(
        self,
        redis: "Redis",
        settings: Settings,
        handlers: Sequence[TaskHandler],
        problem_for: ProblemMapper,
    ) -> None:
        self._redis = redis
        self._settings = settings
        self._handlers: dict[str, TaskHandler] = {
            handler.task_type: handler for handler in handlers
        }
        self._problem_for = problem_for
        self._running: dict[str, asyncio.Task[None]] = {}

    async def run(self) -> None:
        """Consume tasks until cancelled, reconnecting with backoff if Redis fails."""
        attempt = 0
        try:
            while True:
                try:
                    await self._ensure_group()
                    attempt = 0
                    await self._consume()
                except (RedisError, OSError) as error:
                    delay = _RECONNECT_BACKOFF_SECONDS[
                        min(attempt, len(_RECONNECT_BACKOFF_SECONDS) - 1)
                    ]
                    attempt += 1
                    logger.warning("Redis unavailable (%r); retrying in %ss", error, delay)
                    await asyncio.sleep(delay)
        finally:
            for task in self._running.values():
                task.cancel()
            await asyncio.gather(*self._running.values(), return_exceptions=True)

    async def _ensure_group(self) -> None:
        try:
            await self._redis.xgroup_create(
                self._settings.redis_tasks_stream,
                self._settings.redis_consumer_group,
                id="0",
                mkstream=True,
            )
        except ResponseError as error:
            if "BUSYGROUP" not in str(error):
                raise

    async def _consume(self) -> None:
        while True:
            capacity = self._settings.redis_worker_concurrency - len(self._running)
            if capacity <= 0:
                await asyncio.wait(set(self._running.values()), return_when=asyncio.FIRST_COMPLETED)
                continue
            reclaimed = await self._reclaim_stale(capacity)
            entries = reclaimed or await self._read_new(capacity)
            for entry_id, fields in entries:
                self._start(entry_id, fields, reclaimed=bool(reclaimed))
            await asyncio.sleep(0)  # let running tasks progress even if the client never yields

    async def _reclaim_stale(self, count: int) -> list[StreamEntry]:
        reply = await self._redis.xautoclaim(
            self._settings.redis_tasks_stream,
            self._settings.redis_consumer_group,
            self._settings.redis_consumer_name,
            min_idle_time=self._settings.redis_claim_idle_milliseconds,
            start_id="0-0",
            count=count,
        )
        return [
            (entry_id, fields)
            for entry_id, fields in reply[1]
            if fields is not None and entry_id not in self._running
        ]

    async def _read_new(self, count: int) -> list[StreamEntry]:
        reply: Any = await self._redis.xreadgroup(
            self._settings.redis_consumer_group,
            self._settings.redis_consumer_name,
            {self._settings.redis_tasks_stream: ">"},
            count=count,
            block=self._settings.redis_block_milliseconds,
        )
        if not reply:
            return []
        streams = reply.items() if isinstance(reply, dict) else reply
        return [
            (entry_id, fields)
            for _, stream_entries in streams
            for entry_id, fields in stream_entries
            if fields is not None
        ]

    def _start(self, entry_id: str, fields: dict[str, str], *, reclaimed: bool) -> None:
        if entry_id in self._running:
            return
        task = asyncio.create_task(self._process(entry_id, fields, reclaimed=reclaimed))
        self._running[entry_id] = task
        task.add_done_callback(lambda _: self._running.pop(entry_id, None))

    async def _process(self, entry_id: str, fields: dict[str, str], *, reclaimed: bool) -> None:
        heartbeat = asyncio.create_task(self._keep_claimed(entry_id))
        try:
            if reclaimed and await self._deliveries(entry_id) > self._settings.redis_max_deliveries:
                result = self._failed(
                    fields,
                    HTTPStatus.INTERNAL_SERVER_ERROR.value,
                    "La tarea superó el máximo de entregas sin completarse.",
                )
            else:
                result = await self._execute(fields)
            await self._redis.xadd(
                self._settings.redis_results_stream,
                result.to_fields(),  # type: ignore[arg-type]
                maxlen=self._settings.redis_results_max_length,
                approximate=True,
            )
            await self._redis.xack(
                self._settings.redis_tasks_stream, self._settings.redis_consumer_group, entry_id
            )
        except (RedisError, OSError):
            logger.exception("Task %s stays pending: its result could not be published", entry_id)
        finally:
            heartbeat.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat

    async def _execute(self, fields: Mapping[str, str]) -> TaskResult:
        try:
            envelope = TaskEnvelope.from_fields(fields)
        except (json.JSONDecodeError, ValidationError) as error:
            return self._failed(fields, _UNPROCESSABLE, f"La tarea no cumple el contrato: {error}")
        handler = self._handlers.get(envelope.type)
        task_id = str(envelope.task_id)
        if handler is None:
            supported = ", ".join(sorted(self._handlers))
            return self._failed(
                fields,
                _UNPROCESSABLE,
                f"Tipo de tarea «{envelope.type}» desconocido; usa uno de: {supported}.",
            )
        try:
            return TaskResult.succeeded(
                task_id, envelope.type, await handler.handle(envelope.payload)
            )
        except ValidationError as error:
            return self._failed(fields, _UNPROCESSABLE, f"El payload no es válido: {error}")
        except Exception as error:
            return TaskResult.failed(
                task_id, envelope.type, self._problem_for(error, self._instance(fields))
            )

    async def _deliveries(self, entry_id: str) -> int:
        pending = await self._redis.xpending_range(
            self._settings.redis_tasks_stream,
            self._settings.redis_consumer_group,
            min=entry_id,
            max=entry_id,
            count=1,
        )
        return int(pending[0]["times_delivered"]) if pending else 0

    async def _keep_claimed(self, entry_id: str) -> None:
        interval = self._settings.redis_claim_idle_milliseconds / 3 / 1000
        while True:
            await asyncio.sleep(interval)
            with contextlib.suppress(RedisError, OSError):
                await self._redis.xclaim(
                    self._settings.redis_tasks_stream,
                    self._settings.redis_consumer_group,
                    self._settings.redis_consumer_name,
                    min_idle_time=0,
                    message_ids=[entry_id],
                    justid=True,
                )

    def _failed(self, fields: Mapping[str, str], status: int, detail: str) -> TaskResult:
        return TaskResult.failed(
            fields.get("taskId", ""),
            fields.get("type", ""),
            problem_details(status, detail, self._instance(fields)),
        )

    @staticmethod
    def _instance(fields: Mapping[str, str]) -> str:
        return f"tasks/{fields.get('type', '')}/{fields.get('taskId', '')}"
