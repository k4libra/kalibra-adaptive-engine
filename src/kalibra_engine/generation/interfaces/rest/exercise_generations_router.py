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

router = APIRouter(prefix="/api/v1/exercise-generations", tags=["generation"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def generate(
    request: GenerateExercisesRequest,
    service: Annotated[GenerationRunCommandService, Depends(get_generation_run_command_service)],
) -> list[GenerationRunResponse]:
    """Generate verified exercises anchored to the subtopic material (FR-007, FR-012).

    Each run proposes an exercise, verifies it and discards it when verification rejects
    it, until one is approved or the attempts are exhausted. A rejected exercise is never
    returned as ``approvedExercise``; every attempt is returned so curriculum can record
    them (FR-013, FR-031).
    """
    runs = await service.handle(request.to_command())
    return [GenerationRunResponse.from_domain(run) for run in runs]
