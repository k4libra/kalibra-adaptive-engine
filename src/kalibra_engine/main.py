from collections.abc import Sequence

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
from kalibra_engine.verification.dependencies import get_verification_context_facade


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
        version="0.1.0",
        lifespan=build_lifespan(build_task_handlers, exception_handler.problem_for),
    )
    app.include_router(health_router)
    app.include_router(mastery_estimates_router)
    app.include_router(exercise_generations_router)
    app.include_router(curricular_extractions_router)
    exception_handler.register(app)
    return app


app = create_app()
