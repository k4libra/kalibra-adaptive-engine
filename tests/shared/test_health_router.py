import fakeredis
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient
from redis.exceptions import ConnectionError as RedisConnectionError

from kalibra_engine.shared.infrastructure.settings import Settings, get_settings
from kalibra_engine.shared.interfaces.rest.health_router import _redis_health


@pytest.mark.anyio
@pytest.mark.parametrize("path", ["/health/live", "/health"])
async def test_liveness_reports_up(client: AsyncClient, path: str) -> None:
    response = await client.get(path)

    assert response.status_code == 200
    assert response.json() == {"status": "UP", "components": {}}


def _ready(app: FastAPI, settings: Settings) -> tuple[int, dict[str, object]]:
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as http:
        response = http.get("/health/ready")
    return response.status_code, response.json()


def test_readiness_is_up_with_open_client_and_keys(app: FastAPI) -> None:
    status, body = _ready(app, Settings(deepseek_api_key="d", mistral_api_key="m"))  # type: ignore[arg-type]

    assert status == 200
    assert body["status"] == "UP"
    assert set(body["components"]) == {"httpClient", "deepseek", "mistral"}  # type: ignore[arg-type]


def test_readiness_is_down_without_provider_keys(app: FastAPI) -> None:
    status, body = _ready(app, Settings(deepseek_api_key="", mistral_api_key=""))  # type: ignore[arg-type]

    assert status == 503
    assert body["status"] == "DOWN"
    assert body["components"]["deepseek"] == {  # type: ignore[index]
        "status": "DOWN",
        "detail": "API key is not configured.",
    }


def test_readiness_checks_redis_only_when_enabled(app: FastAPI) -> None:
    settings = Settings(deepseek_api_key="d", mistral_api_key="m", redis_enabled=True)  # type: ignore[arg-type]

    status, body = _ready(app, settings)

    assert status == 503
    assert body["components"]["redis"]["status"] == "DOWN"  # type: ignore[index]


@pytest.mark.anyio
async def test_redis_component_up_when_ping_answers() -> None:
    health = await _redis_health(fakeredis.FakeAsyncRedis())

    assert health.status == "UP"


@pytest.mark.anyio
async def test_redis_component_down_when_ping_fails() -> None:
    class Unreachable(fakeredis.FakeAsyncRedis):
        async def ping(self, **_: object) -> bool:
            raise RedisConnectionError("refused")

    health = await _redis_health(Unreachable())

    assert health.status == "DOWN"
    assert health.detail == "Redis did not answer: ConnectionError."
