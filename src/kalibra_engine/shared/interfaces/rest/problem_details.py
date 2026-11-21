from pydantic import Field

from kalibra_engine.shared.interfaces.rest.camel_model import CamelModel


class ProblemDetails(CamelModel):
    """RFC 9457 problem details, as published in the OpenAPI document.

    Documentation only: ``EngineExceptionHandler`` builds the actual bodies, served as
    ``application/problem+json`` over REST and as the ``error`` of a failed queue task.
    """

    type: str = Field(
        description="Problem type URI; the engine always answers `about:blank`.",
        examples=["about:blank"],
    )
    title: str = Field(
        description="Standard reason phrase of the status code.",
        examples=["Bad Gateway"],
    )
    status: int = Field(description="HTTP status code of the problem.", examples=[502])
    detail: str = Field(
        description="Explanation in Spanish; safe to show to a teacher.",
        examples=["Un proveedor externo de IA no respondió correctamente."],
    )
    instance: str = Field(
        description="Request path, or `tasks/{type}/{taskId}` for a queue task.",
        examples=["/api/v1/exercise-generations"],
    )
