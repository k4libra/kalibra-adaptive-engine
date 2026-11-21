import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from kalibra_engine.shared.infrastructure.settings import Settings, get_settings
from tests.conftest import running


@pytest.mark.anyio
@pytest.mark.parametrize("path", ["/health/live", "/health"])
async def test_liveness_reports_up(client: AsyncClient, path: str) -> None:
    response = await client.get(path)

    assert response.status_code == 200
    assert response.json() == {"status": "UP", "components": {}}


async def _ready(app: FastAPI, settings: Settings) -> tuple[int, dict[str, object]]:
    app.dependency_overrides[get_settings] = lambda: settings
    async with running(app) as http:
        response = await http.get("/health/ready")
    return response.status_code, response.json()


@pytest.mark.anyio
async def test_readiness_is_up_with_open_client_and_keys(app: FastAPI) -> None:
    status, body = await _ready(app, Settings(deepseek_api_key="d", mistral_api_key="m"))  # type: ignore[arg-type]

    assert status == 200
    assert body["status"] == "UP"
    assert set(body["components"]) == {"httpClient", "deepseek", "mistral"}  # type: ignore[arg-type]


@pytest.mark.anyio
async def test_readiness_is_down_without_provider_keys(app: FastAPI) -> None:
    status, body = await _ready(app, Settings(deepseek_api_key="", mistral_api_key=""))  # type: ignore[arg-type]

    assert status == 503
    assert body["status"] == "DOWN"
    assert body["components"]["deepseek"] == {  # type: ignore[index]
        "status": "DOWN",
        "detail": "API key is not configured.",
    }


@pytest.mark.anyio
async def test_readiness_without_lifespan_reports_closed_client(client: AsyncClient) -> None:
    response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["components"]["httpClient"]["status"] == "DOWN"
