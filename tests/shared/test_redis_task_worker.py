import asyncio
import contextlib
import json
from collections.abc import Mapping
from typing import Any
from uuid import uuid4

import fakeredis
import pytest
from pydantic import BaseModel, JsonValue
from redis.exceptions import ConnectionError as RedisConnectionError

from kalibra_engine.shared.infrastructure.settings import Settings
from kalibra_engine.shared.interfaces.messaging import redis_task_worker
from kalibra_engine.shared.interfaces.messaging.redis_task_worker import RedisTaskWorker
from kalibra_engine.shared.interfaces.rest.engine_exception_handler import EngineExceptionHandler

TASKS = "kalibra:engine:tasks"
RESULTS = "kalibra:engine:results"
GROUP = "adaptive-engine"


class BusinessRuleBroken(Exception):
    pass


class Strict(BaseModel):
    value: int


class EchoHandler:
    task_type = "echo"

    def __init__(self, delay: float = 0.0) -> None:
        self.calls = 0
        self.delay = delay

    async def handle(self, payload: Mapping[str, Any]) -> JsonValue:
        self.calls += 1
        await asyncio.sleep(self.delay)
        if payload.get("fail") == "business":
            raise BusinessRuleBroken("regla rota")
        if payload.get("fail") == "schema":
            Strict.model_validate(payload)
        return {"echo": dict(payload)}


def _settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "redis_enabled": True,
        "redis_consumer_name": "engine-test",
        "redis_block_milliseconds": 5,
        "redis_claim_idle_milliseconds": 60_000,
        **overrides,
    }
    return Settings(**values)


def _worker(
    redis: fakeredis.FakeAsyncRedis, handler: EchoHandler, **overrides: Any
) -> RedisTaskWorker:
    mapper = EngineExceptionHandler({BusinessRuleBroken: 422}).problem_for
    return RedisTaskWorker(redis, _settings(**overrides), [handler], mapper)


async def _publish(redis: fakeredis.FakeAsyncRedis, **fields: str) -> str:
    return str(await redis.xadd(TASKS, fields))  # type: ignore[arg-type]


def _task(task_type: str = "echo", payload: object | None = None) -> dict[str, str]:
    return {
        "taskId": str(uuid4()),
        "type": task_type,
        "payload": json.dumps({"value": 1} if payload is None else payload),
    }


async def _run_until_results(
    worker: RedisTaskWorker, redis: fakeredis.FakeAsyncRedis, expected: int
) -> list[dict[str, str]]:
    running = asyncio.create_task(worker.run())
    try:
        async with asyncio.timeout(3):
            while await redis.xlen(RESULTS) < expected:
                await asyncio.sleep(0.01)
    finally:
        running.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await running
    return [fields for _, fields in await redis.xrange(RESULTS)]


async def _pending(redis: fakeredis.FakeAsyncRedis) -> int:
    return int((await redis.xpending(TASKS, GROUP))["pending"])


@pytest.fixture
def redis() -> fakeredis.FakeAsyncRedis:
    return fakeredis.FakeAsyncRedis(decode_responses=True)


@pytest.mark.anyio
async def test_success_publishes_result_and_acknowledges(redis: fakeredis.FakeAsyncRedis) -> None:
    task = _task(payload={"value": 7})
    await _publish(redis, **task)

    [result] = await _run_until_results(_worker(redis, EchoHandler()), redis, 1)

    assert result["taskId"] == task["taskId"]
    assert result["type"] == "echo"
    assert result["status"] == "SUCCEEDED"
    assert json.loads(result["result"]) == {"echo": {"value": 7}}
    assert "error" not in result
    assert "completedAt" in result
    assert await _pending(redis) == 0


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("fields", "fragment"),
    [
        ({"taskId": "t-1", "type": "echo", "payload": "{not json"}, "no cumple el contrato"),
        ({"type": "echo", "payload": "{}"}, "no cumple el contrato"),
        (_task(task_type="unknown"), "«unknown» desconocido; usa uno de: echo"),
        (_task(payload={"fail": "schema"}), "El payload no es válido"),
        (_task(payload={"fail": "business"}), "regla rota"),
    ],
)
async def test_failures_are_published_as_problem_details(
    redis: fakeredis.FakeAsyncRedis, fields: dict[str, str], fragment: str
) -> None:
    await _publish(redis, **fields)

    [result] = await _run_until_results(_worker(redis, EchoHandler()), redis, 1)

    assert result["status"] == "FAILED"
    assert "result" not in result
    error = json.loads(result["error"])
    assert error["status"] == 422
    assert fragment in error["detail"]
    assert await _pending(redis) == 0


@pytest.mark.anyio
async def test_stale_task_of_a_dead_consumer_is_reclaimed(redis: fakeredis.FakeAsyncRedis) -> None:
    await redis.xgroup_create(TASKS, GROUP, id="0", mkstream=True)
    await _publish(redis, **_task())
    await redis.xreadgroup(GROUP, "dead-consumer", {TASKS: ">"}, count=1)
    handler = EchoHandler()

    [result] = await _run_until_results(
        _worker(redis, handler, redis_claim_idle_milliseconds=1), redis, 1
    )

    assert result["status"] == "SUCCEEDED"
    assert handler.calls == 1


@pytest.mark.anyio
async def test_task_over_max_deliveries_is_failed_without_running(
    redis: fakeredis.FakeAsyncRedis,
) -> None:
    await redis.xgroup_create(TASKS, GROUP, id="0", mkstream=True)
    entry_id = await _publish(redis, **_task())
    await redis.xreadgroup(GROUP, "dead-consumer", {TASKS: ">"}, count=1)
    await redis.xclaim(TASKS, GROUP, "dead-consumer", min_idle_time=0, message_ids=[entry_id])
    handler = EchoHandler()

    [result] = await _run_until_results(
        _worker(redis, handler, redis_claim_idle_milliseconds=1, redis_max_deliveries=2), redis, 1
    )

    assert result["status"] == "FAILED"
    assert json.loads(result["error"])["status"] == 500
    assert handler.calls == 0
    assert await _pending(redis) == 0


@pytest.mark.anyio
async def test_long_task_keeps_its_claim_and_runs_once(redis: fakeredis.FakeAsyncRedis) -> None:
    await _publish(redis, **_task())
    handler = EchoHandler(delay=0.2)

    await _run_until_results(_worker(redis, handler, redis_claim_idle_milliseconds=60), redis, 1)

    assert handler.calls == 1


@pytest.mark.anyio
async def test_concurrency_is_bounded(redis: fakeredis.FakeAsyncRedis) -> None:
    for _ in range(5):
        await _publish(redis, **_task())
    active = 0
    peak = 0

    class Tracking(EchoHandler):
        async def handle(self, payload: Mapping[str, Any]) -> JsonValue:
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.02)
            active -= 1
            return None

    results = await _run_until_results(
        _worker(redis, Tracking(), redis_worker_concurrency=2), redis, 5
    )

    assert len(results) == 5
    assert peak <= 2


@pytest.mark.anyio
async def test_reconnects_after_redis_failure(
    redis: fakeredis.FakeAsyncRedis, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(redis_task_worker, "_RECONNECT_BACKOFF_SECONDS", (0,))
    failures = iter([RedisConnectionError("down")])
    create_group = redis.xgroup_create

    async def flaky_create(*args: Any, **kwargs: Any) -> Any:
        failure = next(failures, None)
        if failure is not None:
            raise failure
        return await create_group(*args, **kwargs)

    monkeypatch.setattr(redis, "xgroup_create", flaky_create)
    await _publish(redis, **_task())

    [result] = await _run_until_results(_worker(redis, EchoHandler()), redis, 1)

    assert result["status"] == "SUCCEEDED"


@pytest.mark.anyio
async def test_unpublished_result_leaves_task_pending(
    redis: fakeredis.FakeAsyncRedis, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def failing_xadd(*_: Any, **__: Any) -> Any:
        raise RedisConnectionError("down")

    await _publish(redis, **_task())
    monkeypatch.setattr(redis, "xadd", failing_xadd)
    handler = EchoHandler()
    running = asyncio.create_task(_worker(redis, handler).run())
    try:
        async with asyncio.timeout(3):
            while handler.calls == 0:
                await asyncio.sleep(0.01)
        await asyncio.sleep(0.05)
    finally:
        running.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await running

    assert await _pending(redis) == 1
