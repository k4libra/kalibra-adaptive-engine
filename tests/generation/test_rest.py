import json
from collections.abc import AsyncIterator, Callable
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from kalibra_engine.shared.infrastructure.http_client import get_http_client
from kalibra_engine.shared.infrastructure.settings import Settings, get_settings

Handler = Callable[[httpx.Request], httpx.Response]

GENERATIONS = "/api/v1/exercise-generations"
EXTRACTIONS = "/api/v1/curricular-extractions"


def _chat(content: dict[str, object]) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(content)}}]})


def _draft(difficulty: str = "EASY") -> dict[str, object]:
    return {
        "statement": "¿Derivada de x^2?",
        "options": [
            {"key": k, "text": t} for k, t in zip("ABCD", ("2x", "x", "x^2", "2"), strict=True)
        ],
        "correct_option_key": "A",
        "explanation": "Regla de la potencia.",
        "difficulty": difficulty,
    }


def _review(solved_key: str) -> dict[str, object]:
    return {"solved_option_key": solved_key, "difficulty_matches": True, "justification": "ok"}


@pytest.fixture
def provider_routes() -> dict[str, list[httpx.Response]]:
    return {"deepseek-v4-flash": [], "deepseek-v4-pro": [], "ocr": []}


@pytest.fixture
async def engine(
    app: FastAPI, provider_routes: dict[str, list[httpx.Response]]
) -> AsyncIterator[AsyncClient]:
    def route(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/v1/ocr"):
            return provider_routes["ocr"].pop(0)
        model = json.loads(request.read())["model"]
        return provider_routes[model].pop(0)

    providers = httpx.AsyncClient(transport=httpx.MockTransport(route))

    async def provider_client() -> httpx.AsyncClient:
        return providers

    app.dependency_overrides[get_http_client] = provider_client
    app.dependency_overrides[get_settings] = lambda: Settings(
        deepseek_api_key="ds",  # type: ignore[arg-type]
        mistral_api_key="ms",  # type: ignore[arg-type]
        generation_max_attempts=2,
        provider_max_retries=1,
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http
    await providers.aclose()


def _generation_request(**overrides: object) -> dict[str, object]:
    return {
        "courseId": str(uuid4()),
        "subtopicId": str(uuid4()),
        "subtopicName": "Derivadas",
        "normalizedContent": "Regla de la potencia.",
        "quantity": 1,
        **overrides,
    }


@pytest.mark.anyio
async def test_rejected_exercise_is_discarded_and_regenerated(
    engine: AsyncClient, provider_routes: dict[str, list[httpx.Response]]
) -> None:
    provider_routes["deepseek-v4-flash"] += [_chat(_draft()), _chat(_draft())]
    provider_routes["deepseek-v4-pro"] += [_chat(_review("B")), _chat(_review("A"))]

    response = await engine.post(GENERATIONS, json=_generation_request())

    assert response.status_code == 201
    [run] = response.json()
    assert run["exhausted"] is False
    assert run["approvedExercise"]["options"] == ["2x", "x", "x^2", "2"]
    first, second = run["attempts"]
    assert first["approved"] is False
    assert "«B»" in first["rejectionReason"]
    assert first["usedFallback"] is True
    assert second["approved"] is True
    assert second["rejectionReason"] is None


@pytest.mark.anyio
async def test_exhausted_run_never_exposes_a_rejected_exercise(
    engine: AsyncClient, provider_routes: dict[str, list[httpx.Response]]
) -> None:
    provider_routes["deepseek-v4-flash"] += [_chat(_draft("HARD")), _chat(_draft("HARD"))]

    response = await engine.post(GENERATIONS, json=_generation_request())

    [run] = response.json()
    assert run["exhausted"] is True
    assert run["approvedExercise"] is None
    assert [attempt["difficultyPassed"] for attempt in run["attempts"]] == [False, False]
    assert provider_routes["deepseek-v4-pro"] == []


@pytest.mark.anyio
async def test_provider_outage_is_bad_gateway(
    engine: AsyncClient, provider_routes: dict[str, list[httpx.Response]]
) -> None:
    provider_routes["deepseek-v4-flash"] += [httpx.Response(401)]

    response = await engine.post(GENERATIONS, json=_generation_request())

    assert response.status_code == 502
    assert response.headers["content-type"] == "application/problem+json"


@pytest.mark.anyio
async def test_generation_without_deepseek_key_is_bad_gateway(
    app: FastAPI, engine: AsyncClient
) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        deepseek_api_key="",  # type: ignore[arg-type]
    )

    response = await engine.post(GENERATIONS, json=_generation_request())

    assert response.status_code == 502
    assert response.headers["content-type"] == "application/problem+json"


@pytest.mark.anyio
@pytest.mark.parametrize(
    "overrides",
    [{"quantity": 0}, {"quantity": 11}, {"masteryProbability": 1.2}, {"subtopicName": ""}],
)
async def test_invalid_generation_request_is_rejected(
    engine: AsyncClient, overrides: dict[str, object]
) -> None:
    response = await engine.post(GENERATIONS, json=_generation_request(**overrides))

    assert response.status_code == 422


def _extraction_request(**overrides: object) -> dict[str, object]:
    return {
        "materialId": str(uuid4()),
        "storageReference": "https://files.test/material.pdf",
        "format": "pdf",
        **overrides,
    }


@pytest.mark.anyio
async def test_extraction_returns_normalized_content(
    engine: AsyncClient, provider_routes: dict[str, list[httpx.Response]]
) -> None:
    provider_routes["ocr"].append(
        httpx.Response(200, json={"pages": [{"markdown": "# Tema\n\n\n\nx²"}, {"markdown": "Fin"}]})
    )

    response = await engine.post(EXTRACTIONS, json=_extraction_request())

    assert response.status_code == 201
    assert response.json() == {"normalizedText": "# Tema\n\nx²\n\nFin", "pageCount": 2}


@pytest.mark.anyio
@pytest.mark.parametrize("provider_status", [400, 413, 415, 422])
async def test_document_rejected_by_provider_is_an_ingestion_error(
    engine: AsyncClient, provider_routes: dict[str, list[httpx.Response]], provider_status: int
) -> None:
    provider_routes["ocr"].append(httpx.Response(provider_status))

    response = await engine.post(EXTRACTIONS, json=_extraction_request())

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert "No se pudo extraer" in response.json()["detail"]


@pytest.mark.anyio
async def test_material_without_text_is_an_ingestion_error(
    engine: AsyncClient, provider_routes: dict[str, list[httpx.Response]]
) -> None:
    provider_routes["ocr"].append(httpx.Response(200, json={"pages": []}))

    response = await engine.post(EXTRACTIONS, json=_extraction_request())

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert "no contiene texto" in response.json()["detail"]


@pytest.mark.anyio
async def test_unsupported_format_is_an_ingestion_error(engine: AsyncClient) -> None:
    response = await engine.post(EXTRACTIONS, json=_extraction_request(format="exe"))

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert "no está soportado" in response.json()["detail"]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "provider_response",
    [
        httpx.Response(401),
        httpx.Response(403),
        httpx.Response(404),
        httpx.Response(408),
        httpx.Response(429),
        httpx.Response(500),
        httpx.Response(503),
        httpx.Response(200, text="not json"),
        httpx.Response(200, json={"unexpected": "shape"}),
    ],
)
async def test_extraction_provider_failure_is_bad_gateway_not_a_bad_material(
    engine: AsyncClient,
    provider_routes: dict[str, list[httpx.Response]],
    provider_response: httpx.Response,
) -> None:
    provider_routes["ocr"].append(provider_response)

    response = await engine.post(EXTRACTIONS, json=_extraction_request())

    assert response.status_code == 502
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["detail"] == "Un proveedor externo de IA no respondió correctamente."


@pytest.mark.anyio
async def test_extraction_without_mistral_key_is_bad_gateway(
    app: FastAPI, engine: AsyncClient
) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        deepseek_api_key="ds",  # type: ignore[arg-type]
        mistral_api_key="",  # type: ignore[arg-type]
    )

    response = await engine.post(EXTRACTIONS, json=_extraction_request())

    assert response.status_code == 502
    assert response.headers["content-type"] == "application/problem+json"


@pytest.mark.anyio
async def test_extraction_transport_failure_is_bad_gateway(app: FastAPI) -> None:
    def unreachable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    providers = httpx.AsyncClient(transport=httpx.MockTransport(unreachable))

    async def provider_client() -> httpx.AsyncClient:
        return providers

    app.dependency_overrides[get_http_client] = provider_client
    app.dependency_overrides[get_settings] = lambda: Settings(
        mistral_api_key="ms",  # type: ignore[arg-type]
        provider_max_retries=1,
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        response = await http.post(EXTRACTIONS, json=_extraction_request())
    await providers.aclose()

    assert response.status_code == 502


@pytest.mark.anyio
async def test_extraction_requires_https_reference(engine: AsyncClient) -> None:
    response = await engine.post(
        EXTRACTIONS, json=_extraction_request(storageReference="file:///etc/passwd")
    )

    assert response.status_code == 422
