from typing import Literal
from uuid import UUID

from pydantic import Field

from kalibra_engine.mastery.domain.model.commands.estimate_mastery_command import (
    EstimateMasteryCommand,
)
from kalibra_engine.mastery.domain.model.valueobjects.answer_outcome import AnswerOutcome
from kalibra_engine.shared.interfaces.rest.camel_model import CamelModel


class EstimateMasteryRequest(CamelModel):
    """Answer submitted by a student, sent by kalibra-api (progress)."""

    student_id: UUID = Field(
        description="Student who answered.",
        examples=["8f14e45f-ceea-467a-9575-000000000001"],
    )
    subtopic_id: UUID = Field(
        description="Subtopic of the exercise; selects the BKT parameters.",
        examples=["8f14e45f-ceea-467a-9575-000000000002"],
    )
    prior_probability: float | None = Field(
        default=None,
        description="Latest stored mastery in [0, 1]; omit it when the student has no history.",
        examples=[0.42],
    )
    outcome: Literal["CORRECT", "INCORRECT"] = Field(
        description="Whether the student's answer was correct.", examples=["CORRECT"]
    )

    def to_command(self) -> EstimateMasteryCommand:
        """Translate the request into the domain command.

        Returns:
            The estimation command.
        """
        return EstimateMasteryCommand(
            student_id=self.student_id,
            subtopic_id=self.subtopic_id,
            prior_probability=self.prior_probability,
            outcome=AnswerOutcome(self.outcome),
        )
