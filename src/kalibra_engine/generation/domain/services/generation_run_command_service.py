from typing import Protocol

from kalibra_engine.generation.domain.model.aggregates.generation_run import GenerationRun
from kalibra_engine.generation.domain.model.commands.generate_exercises_command import (
    GenerateExercisesCommand,
)


class GenerationRunCommandService(Protocol):
    """Command service that generates verified exercises."""

    async def handle(self, command: GenerateExercisesCommand) -> list[GenerationRun]:
        """Generate ``command.quantity`` exercises, one run each.

        Args:
            command: The generation request.

        Returns:
            One finished run per requested exercise: approved or exhausted.
        """
        ...
