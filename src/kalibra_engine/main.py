from collections.abc import Sequence
from importlib.metadata import PackageNotFoundError, version

import httpx
from fastapi import FastAPI, status

from kalibra_engine.generation.dependencies import (
    get_curricular_extraction_command_service,
    get_generation_run_command_service,
)
from kalibra_engine.generation.domain.exceptions.content_extraction_failed_exception import (
    ContentExtractionFailedException,
)
from kalibra_engine.generation.domain.exceptions.generation_attempts_exhausted_exception import (
    GenerationAttemptsExhaustedException,
)
from kalibra_engine.generation.interfaces.messaging.curricular_extractions_task_handler import (
    CurricularExtractionsTaskHandler,
)
from kalibra_engine.generation.interfaces.messaging.exercise_generations_task_handler import (
    ExerciseGenerationsTaskHandler,
)
from kalibra_engine.generation.interfaces.rest.curricular_extractions_router import (
    router as curricular_extractions_router,
)
from kalibra_engine.generation.interfaces.rest.exercise_generations_router import (
    router as exercise_generations_router,
)
from kalibra_engine.mastery.dependencies import (
    get_bkt_parameters_settings,
    get_mastery_estimation_command_service,
)
from kalibra_engine.mastery.domain.exceptions.invalid_probability_exception import (
    InvalidProbabilityException,
)
from kalibra_engine.mastery.interfaces.messaging.mastery_estimates_task_handler import (
    MasteryEstimatesTaskHandler,
)
from kalibra_engine.mastery.interfaces.rest.mastery_estimates_router import (
    router as mastery_estimates_router,
)
from kalibra_engine.shared.infrastructure.lifespan import build_lifespan
from kalibra_engine.shared.infrastructure.settings import Settings
from kalibra_engine.shared.interfaces.messaging.task_handler import TaskHandler
from kalibra_engine.shared.interfaces.rest.engine_exception_handler import EngineExceptionHandler
from kalibra_engine.shared.interfaces.rest.health_router import router as health_router
from kalibra_engine.shared.interfaces.rest.problem_responses import document_problem_schemas
from kalibra_engine.verification.dependencies import get_verification_context_facade

_DISTRIBUTION = "kalibra-adaptive-engine"
_UNKNOWN_VERSION = "0.0.0"

_DESCRIPTION = """\
Stateless AI service of Kalibra. It computes and returns; it stores nothing, has no
authentication and is meant to be reachable only by **kalibra-api**, its single consumer,
which owns every user, course, material, answer and persisted result.

### What it does

- **Mastery**: Bayesian Knowledge Tracing update of a student's mastery of a subtopic
  after each answer. Needs no AI provider.
- **Generation**: multiple-choice exercises with four options, anchored to the subtopic
  material and adjusted to the student's mastery (DeepSeek V4-Flash).
- **Extraction**: OCR of teacher material and normalization of its text (Mistral OCR).
- **Verification** has **no endpoint**: it runs in-process inside generation. Every
  proposed exercise is checked for technical correctness and difficulty (rules first,
  DeepSeek V4-Pro to solve what rules cannot judge) and discarded with a reason when it
  does not conform.

### Two transports, one contract

kalibra-api either calls these REST endpoints, or publishes a task on the Redis stream
`kalibra:engine:tasks` and reads the outcome from `kalibra:engine:results`. The task
`type` is the REST resource name (`mastery-estimates`, `exercise-generations`,
`curricular-extractions`), its `payload` is exactly the request body documented here and
its `result` exactly the `201` response body. Failures are the same RFC 9457 problem
details in both transports. JSON is `camelCase`.

### Status codes

- `201`: computed; kalibra-api persists the body.
- `409`: a generation run was asked for an attempt beyond its limit. Do not retry; it
  needs attention.
- `422`: the input or the material is bad. Do not retry; for extraction, mark the
  material as an ingestion error so the teacher replaces it.
- `502`: an AI provider failed, is unreachable or is not configured. Retry later.

Problems are served as `application/problem+json`. A request that does not match the
schema is rejected by the framework with `422` and its own `application/json` body
(`detail` is a list of field errors).
"""

_OPENAPI_TAGS = [
    {
        "name": "Mastery",
        "description": (
            "Bayesian Knowledge Tracing estimate of a student's mastery of a subtopic "
            "after each answer. Returns the prior and the posterior so the consumer can "
            "show the change. Works without provider keys."
        ),
    },
    {
        "name": "Generation",
        "description": (
            "Multiple-choice exercises anchored to the subtopic material and adjusted to "
            "the student's mastery (DeepSeek V4-Flash). Each exercise is verified "
            "in-process before it can be returned as approved; every attempt is returned."
        ),
    },
    {
        "name": "Extraction",
        "description": (
            "OCR of curricular material (Mistral OCR) and normalization of its text, "
            "which kalibra-api stores as the curricular anchor for generation."
        ),
    },
    {
        "name": "Health",
        "description": "Liveness and readiness probes for the container platform.",
    },
]


def engine_version() -> str:
    """Read the engine version from the installed package metadata.

    Returns:
        The distribution version, or ``0.0.0`` when the package is not installed (source
        tree on the path without an installation).
    """
    try:
        return version(_DISTRIBUTION)
    except PackageNotFoundError:
        return _UNKNOWN_VERSION


async def build_task_handlers(
    client: httpx.AsyncClient, settings: Settings
) -> Sequence[TaskHandler]:
    """Compose the queue handlers from the same composition roots used by REST.

    Args:
        client: Shared outbound client.
        settings: Engine settings.

    Returns:
        One handler per task type.
    """
    verification_context_facade = await get_verification_context_facade(client, settings)
    return [
        MasteryEstimatesTaskHandler(
            await get_mastery_estimation_command_service(get_bkt_parameters_settings())
        ),
        ExerciseGenerationsTaskHandler(
            await get_generation_run_command_service(client, settings, verification_context_facade)
        ),
        CurricularExtractionsTaskHandler(
            await get_curricular_extraction_command_service(client, settings)
        ),
    ]


def create_app() -> FastAPI:
    """Compose the Kalibra Adaptive Engine application.

    Returns:
        The configured FastAPI application.
    """
    exception_handler = EngineExceptionHandler(
        status_by_exception={
            InvalidProbabilityException: status.HTTP_422_UNPROCESSABLE_CONTENT,
            ContentExtractionFailedException: status.HTTP_422_UNPROCESSABLE_CONTENT,
            GenerationAttemptsExhaustedException: status.HTTP_409_CONFLICT,
        }
    )
    app = FastAPI(
        title="Kalibra Adaptive Engine",
        summary="Mastery estimation, exercise generation and verification for Kalibra.",
        description=_DESCRIPTION,
        version=engine_version(),
        openapi_tags=_OPENAPI_TAGS,
        lifespan=build_lifespan(build_task_handlers, exception_handler.problem_for),
    )
    app.include_router(mastery_estimates_router)
    app.include_router(exercise_generations_router)
    app.include_router(curricular_extractions_router)
    app.include_router(health_router)
    exception_handler.register(app)
    document_problem_schemas(app)
    return app


app = create_app()
