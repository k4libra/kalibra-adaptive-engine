from typing import Any

import pytest
from httpx import AsyncClient

from kalibra_engine.main import engine_version

PROBLEM_JSON = "application/problem+json"
PROBLEM_SCHEMA = {"$ref": "#/components/schemas/ProblemDetails"}
VALIDATION_SCHEMA = {"$ref": "#/components/schemas/HTTPValidationError"}

OPERATIONS = {
    ("post", "/api/v1/mastery-estimates"): ("Mastery", {"201", "422"}),
    ("post", "/api/v1/exercise-generations"): ("Generation", {"201", "409", "422", "502"}),
    ("post", "/api/v1/curricular-extractions"): ("Extraction", {"201", "422", "502"}),
    ("get", "/health/live"): ("Health", {"200"}),
    ("get", "/health/ready"): ("Health", {"200", "503"}),
}


@pytest.fixture
async def document(client: AsyncClient) -> dict[str, Any]:
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    return body


def _operations(document: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (method, path): operation
        for path, methods in document["paths"].items()
        for method, operation in methods.items()
    }


@pytest.mark.anyio
async def test_info_describes_the_service(document: dict[str, Any]) -> None:
    info = document["info"]

    assert info["title"] == "Kalibra Adaptive Engine"
    assert info["version"] == engine_version() != "0.0.0"
    for expected in ("kalibra-api", "Stateless", "kalibra:engine:tasks", "no endpoint"):
        assert expected in info["description"]
    for status in ("`409`", "`422`", "`502`"):
        assert status in info["description"]


@pytest.mark.anyio
async def test_tags_are_ordered_and_described(document: dict[str, Any]) -> None:
    tags = document["tags"]

    assert [tag["name"] for tag in tags] == ["Mastery", "Generation", "Extraction", "Health"]
    assert all(tag["description"] for tag in tags)


@pytest.mark.anyio
async def test_every_operation_has_its_tag_summary_and_documented_responses(
    document: dict[str, Any],
) -> None:
    operations = _operations(document)

    assert set(operations) == set(OPERATIONS)
    for key, (tag, statuses) in OPERATIONS.items():
        operation = operations[key]
        assert operation["tags"] == [tag], key
        assert operation["summary"], key
        assert operation["description"], key
        assert set(operation["responses"]) == statuses, key
        assert all(response["description"] for response in operation["responses"].values()), key


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("path", "status"),
    [
        ("/api/v1/mastery-estimates", "422"),
        ("/api/v1/exercise-generations", "409"),
        ("/api/v1/exercise-generations", "502"),
        ("/api/v1/curricular-extractions", "422"),
        ("/api/v1/curricular-extractions", "502"),
    ],
)
async def test_engine_errors_are_documented_as_problem_json(
    document: dict[str, Any], path: str, status: str
) -> None:
    content = document["paths"][path]["post"]["responses"][status]["content"]

    assert content[PROBLEM_JSON]["schema"] == PROBLEM_SCHEMA
    assert content[PROBLEM_JSON]["example"]["status"] == int(status)
    assert content[PROBLEM_JSON]["example"]["instance"] == path
    expected_media_types = {PROBLEM_JSON} | ({"application/json"} if status == "422" else set())
    assert set(content) == expected_media_types


@pytest.mark.anyio
@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/mastery-estimates",
        "/api/v1/exercise-generations",
        "/api/v1/curricular-extractions",
    ],
)
async def test_request_validation_is_documented_as_plain_json(
    document: dict[str, Any], path: str
) -> None:
    content = document["paths"][path]["post"]["responses"]["422"]["content"]

    assert content["application/json"]["schema"] == VALIDATION_SCHEMA


@pytest.mark.anyio
async def test_problem_details_schema_matches_the_handler_output(
    document: dict[str, Any],
) -> None:
    schemas = document["components"]["schemas"]

    assert set(schemas["ProblemDetails"]["properties"]) == {
        "type",
        "title",
        "status",
        "detail",
        "instance",
    }
    assert {"HTTPValidationError", "ValidationError"} <= set(schemas)


@pytest.mark.anyio
async def test_every_schema_field_is_described_with_an_example(
    document: dict[str, Any],
) -> None:
    framework_schemas = {"HTTPValidationError", "ValidationError"}
    nested = {"exercise", "approvedExercise", "attempts"}

    for name, schema in document["components"]["schemas"].items():
        if name in framework_schemas:
            continue
        for field, definition in schema["properties"].items():
            assert definition.get("description"), f"{name}.{field}"
            if field not in nested:
                assert "examples" in definition, f"{name}.{field}"


@pytest.mark.anyio
async def test_wire_field_names_stay_camel_case(document: dict[str, Any]) -> None:
    schemas = document["components"]["schemas"]

    assert set(schemas["EstimateMasteryRequest"]["properties"]) == {
        "studentId",
        "subtopicId",
        "priorProbability",
        "outcome",
    }
    assert set(schemas["GenerationRunResponse"]["properties"]) == {
        "approvedExercise",
        "attempts",
        "exhausted",
    }
    assert set(schemas["ExtractContentRequest"]["properties"]) == {
        "materialId",
        "storageReference",
        "format",
    }


@pytest.mark.anyio
async def test_swagger_ui_is_served(client: AsyncClient) -> None:
    response = await client.get("/docs")

    assert response.status_code == 200
    assert "swagger-ui" in response.text
