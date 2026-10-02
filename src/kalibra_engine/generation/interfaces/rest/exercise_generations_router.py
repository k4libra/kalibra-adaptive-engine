from typing import Annotated

from fastapi import APIRouter, Depends, status

from kalibra_engine.generation.dependencies import get_generation_run_command_service
from kalibra_engine.generation.domain.services.generation_run_command_service import (
    GenerationRunCommandService,
)
from kalibra_engine.generation.interfaces.rest.schemas.generate_exercises_request import (
    GenerateExercisesRequest,
)
from kalibra_engine.generation.interfaces.rest.schemas.generation_run_response import (
    GenerationRunResponse,
)
from kalibra_engine.shared.interfaces.rest.problem_responses import problem_response

_PATH = "/api/v1/exercise-generations"

router = APIRouter(prefix=_PATH, tags=["Generation"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Generate verified exercises",
    response_description=(
        "One run per requested exercise, in request order, each with every attempt."
    ),
    responses={
        status.HTTP_409_CONFLICT: problem_response(
            "A generation run was asked for an attempt beyond its limit; do not retry. "
            "A run that simply uses all its attempts is not an error: it answers `201` "
            "with `exhausted: true`.",
            status=status.HTTP_409_CONFLICT,
            detail="La generación ya agotó sus 3 intentos sin un ejercicio aprobado.",
            instance=_PATH,
        ),
        status.HTTP_502_BAD_GATEWAY: problem_response(
            "DeepSeek is unreachable, not configured (missing `DEEPSEEK_API_KEY`) or "
            "answered badly after the engine's own retries; retry later. No partial "
            "result is returned.",
            status=status.HTTP_502_BAD_GATEWAY,
            detail="Un proveedor externo de IA no respondió correctamente.",
            instance=_PATH,
        ),
    },
)
async def generate(
    request: GenerateExercisesRequest,
    service: Annotated[GenerationRunCommandService, Depends(get_generation_run_command_service)],
) -> list[GenerationRunResponse]:
    """Generate verified exercises anchored to the subtopic material.

    The target difficulty comes from the student's mastery: `EASY` below 0.40 or without
    an estimate, `MEDIUM` up to 0.70, `HARD` above. Each run asks DeepSeek V4-Flash for a
    four-option exercise anchored to the subtopic material, verifies it and discards it
    when verification rejects it, until one is approved or the attempts are exhausted.

    Verification has no endpoint: it runs in-process inside this operation. Rules check
    the structure and the declared difficulty; exercises the rules cannot fault are solved
    independently by DeepSeek V4-Pro.

    A rejected exercise is never returned as `approvedExercise`. Every attempt, approved
    or discarded, is returned with its rejection reason so kalibra-api can record them.
    A malformed request answers `422` with FastAPI's validation body; do not retry it.
    """
    runs = await service.handle(request.to_command())
    return [GenerationRunResponse.from_domain(run) for run in runs]
