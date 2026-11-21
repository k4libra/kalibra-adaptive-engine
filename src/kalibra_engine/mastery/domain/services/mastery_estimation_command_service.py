from typing import Protocol

from kalibra_engine.mastery.domain.model.commands.estimate_mastery_command import (
    EstimateMasteryCommand,
)
from kalibra_engine.mastery.domain.model.valueobjects.mastery_estimate import MasteryEstimate


class MasteryEstimationCommandService(Protocol):
    """Command service of the mastery bounded context."""

    def handle(self, command: EstimateMasteryCommand) -> MasteryEstimate:
        """Estimate mastery after an answer.

        Args:
            command: The estimation request.

        Returns:
            The updated estimate; the engine is stateless, so progress persists it.
        """
        ...
