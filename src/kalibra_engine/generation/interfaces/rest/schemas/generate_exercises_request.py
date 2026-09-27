from uuid import UUID

from pydantic import Field

from kalibra_engine.generation.domain.model.commands.generate_exercises_command import (
    GenerateExercisesCommand,
)
from kalibra_engine.generation.domain.model.valueobjects.curricular_context import (
    CurricularContext,
)
from kalibra_engine.shared.interfaces.rest.camel_model import CamelModel


class GenerateExercisesRequest(CamelModel):
    """Exercise generation request sent by kalibra-api (curriculum)."""

    course_id: UUID
    subtopic_id: UUID
    subtopic_name: str = Field(min_length=1)
    normalized_content: str = Field(
        min_length=1, description="Normalized material of the subtopic (curricular anchor)."
    )
    mastery_probability: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Student's mastery; omit it for teacher requests or students without history.",
    )
    quantity: int = Field(ge=1, le=10)

    def to_command(self) -> GenerateExercisesCommand:
        """Translate the request into the domain command.

        Returns:
            The generation command.
        """
        return GenerateExercisesCommand(
            course_id=self.course_id,
            subtopic_id=self.subtopic_id,
            context=CurricularContext(
                subtopic_name=self.subtopic_name, normalized_content=self.normalized_content
            ),
            mastery_probability=self.mastery_probability,
            quantity=self.quantity,
        )
