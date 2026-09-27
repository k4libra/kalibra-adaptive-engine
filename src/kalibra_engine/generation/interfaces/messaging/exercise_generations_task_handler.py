from collections.abc import Mapping
from typing import Any

from pydantic import JsonValue

from kalibra_engine.generation.domain.services.generation_run_command_service import (
    GenerationRunCommandService,
)
from kalibra_engine.generation.interfaces.rest.schemas.generate_exercises_request import (
    GenerateExercisesRequest,
)
from kalibra_engine.generation.interfaces.rest.schemas.generation_run_response import (
    GenerationRunResponse,
)


class ExerciseGenerationsTaskHandler:
    """Queue entry to generation: same contract as ``POST /api/v1/exercise-generations``.

    Args:
        service: Generation command service.
    """

    task_type = "exercise-generations"

    def __init__(self, service: GenerationRunCommandService) -> None:
        self._service = service

    async def handle(self, payload: Mapping[str, Any]) -> JsonValue:
        """Generate verified exercises.

        Args:
            payload: ``GenerateExercisesRequest`` body.

        Returns:
            A list of ``GenerationRunResponse`` bodies.
        """
        request = GenerateExercisesRequest.model_validate(payload)
        runs = await self._service.handle(request.to_command())
        return [GenerationRunResponse.from_domain(run).model_dump(mode="json") for run in runs]
