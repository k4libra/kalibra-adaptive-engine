import httpx
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from kalibra_engine.shared.infrastructure.external_provider_error import ExternalProviderError
from kalibra_engine.shared.interfaces.rest.engine_exception_handler import EngineExceptionHandler


class BusinessRuleBroken(Exception):
    pass


class SpecificBusinessRuleBroken(BusinessRuleBroken):
    pass


def _app_raising(error: Exception) -> FastAPI:
    app = FastAPI()

    @app.get("/boom")
    async def boom() -> None:
        raise error

    EngineExceptionHandler(status_by_exception={BusinessRuleBroken: 422}).register(app)
    return app


async def _get_boom(app: FastAPI) -> httpx.Response:
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        return await http.get("/boom")


@pytest.mark.anyio
async def test_mapped_exception_becomes_problem_details() -> None:
    response = await _get_boom(_app_raising(BusinessRuleBroken("regla rota")))

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json() == {
        "type": "about:blank",
        "title": "Unprocessable Content",
        "status": 422,
        "detail": "regla rota",
        "instance": "/boom",
    }


@pytest.mark.anyio
async def test_subclass_uses_parent_mapping() -> None:
    response = await _get_boom(_app_raising(SpecificBusinessRuleBroken("detalle")))

    assert response.status_code == 422


@pytest.mark.anyio
@pytest.mark.parametrize(
    "error",
    [ExternalProviderError("deepseek", "bad json"), httpx.ConnectError("refused")],
)
async def test_provider_failures_become_bad_gateway_without_leaking_details(
    error: Exception,
) -> None:
    response = await _get_boom(_app_raising(error))

    assert response.status_code == 502
    assert response.json()["detail"] == "Un proveedor externo de IA no respondió correctamente."
