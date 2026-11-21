from typing import Protocol

from kalibra_engine.verification.domain.model.aggregates.exercise_verification import (
    ExerciseVerification,
)
from kalibra_engine.verification.domain.model.commands.verify_exercise_command import (
    VerifyExerciseCommand,
)


class ExerciseVerificationCommandService(Protocol):
    """Command service of the verification bounded context."""

    async def handle(self, command: VerifyExerciseCommand) -> ExerciseVerification:
        """Verify an exercise and reach a verdict.

        Args:
            command: The verification request.

        Returns:
            The decided verification.
        """
        ...
