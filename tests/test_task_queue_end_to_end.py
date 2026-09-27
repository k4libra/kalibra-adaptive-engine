import asyncio
import json
from uuid import uuid4

import fakeredis
import pytest

from kalibra_engine.main import create_app
from kalibra_engine.shared.infrastructure import lifespan as lifespan_module
from kalibra_engine.shared.infrastructure.settings import Settings
from tests.conftest import running


@pytest.mark.anyio
async def test_mastery_task_published_by_kalibra_api_gets_a_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = fakeredis.FakeServer()
    settings = Settings(
        redis_enabled=True, redis_block_milliseconds=5, redis_consumer_name="engine-e2e"
    )
    monkeypatch.setattr(lifespan_module, "get_settings", lambda: settings)
    monkeypatch.setattr(
        lifespan_module,
        "create_redis_client",
        lambda _: fakeredis.FakeAsyncRedis(server=server, decode_responses=True),
    )
    kalibra_api = fakeredis.FakeAsyncRedis(server=server, decode_responses=True)
    task_id = str(uuid4())

    async with running(create_app()):
        await kalibra_api.xadd(
            settings.redis_tasks_stream,
            {
                "taskId": task_id,
                "type": "mastery-estimates",
                "payload": json.dumps(
                    {"studentId": str(uuid4()), "subtopicId": str(uuid4()), "outcome": "CORRECT"}
                ),
            },
        )
        async with asyncio.timeout(3):
            while await kalibra_api.xlen(settings.redis_results_stream) == 0:
                await asyncio.sleep(0.02)

    [(_, result)] = await kalibra_api.xrange(settings.redis_results_stream)
    assert result["taskId"] == task_id
    assert result["status"] == "SUCCEEDED"
    body = json.loads(result["result"])
    assert body["initializedFromBase"] is True
    assert body["level"] == "MEDIUM"
