from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import (
    validation_error_definition,
    validation_error_response_definition,
)

from kalibra_engine.shared.interfaces.rest.engine_exception_handler import (
    PROBLEM_JSON,
    problem_details,
)
from kalibra_engine.shared.interfaces.rest.problem_details import ProblemDetails

_SCHEMAS = "#/components/schemas/"


def problem_response(
    description: str,
    *,
    status: int,
    detail: str,
    instance: str,
    with_request_validation: bool = False,
) -> dict[str, Any]:
    """Document one problem-details response of a path operation.

    Args:
        description: When the endpoint answers with this status (Markdown).
        status: HTTP status code, used in the example body.
        detail: Example ``detail``, in Spanish as the engine writes it.
        instance: Example ``instance`` (the request path).
        with_request_validation: Also document FastAPI's own validation body, which the
            same status code carries as ``application/json`` when the request is malformed.

    Returns:
        The OpenAPI response object for the ``responses`` argument of a route.
    """
    content: dict[str, Any] = {
        PROBLEM_JSON: {
            "schema": {"$ref": f"{_SCHEMAS}{ProblemDetails.__name__}"},
            "example": problem_details(status, detail, instance),
        }
    }
    if with_request_validation:
        content["application/json"] = {"schema": {"$ref": f"{_SCHEMAS}HTTPValidationError"}}
    return {"description": description, "content": content}


def document_problem_schemas(app: FastAPI) -> None:
    """Publish the schemas referenced by ``problem_response`` in the OpenAPI document.

    FastAPI only registers the models it finds in ``application/json`` responses, so the
    schemas used under ``application/problem+json`` are added to the generated document.

    Args:
        app: The FastAPI application.
    """
    generate = app.openapi

    def openapi() -> dict[str, Any]:
        document = generate()
        schemas = document.setdefault("components", {}).setdefault("schemas", {})
        schemas.setdefault(ProblemDetails.__name__, ProblemDetails.model_json_schema())
        schemas.setdefault("ValidationError", validation_error_definition)
        schemas.setdefault("HTTPValidationError", validation_error_response_definition)
        return document

    app.openapi = openapi  # type: ignore[method-assign]
