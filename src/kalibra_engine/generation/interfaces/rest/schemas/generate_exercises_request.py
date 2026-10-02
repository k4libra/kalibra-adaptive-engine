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

    course_id: UUID = Field(
        description="Course of the subtopic.",
        examples=["8f14e45f-ceea-467a-9575-000000000004"],
    )
    subtopic_id: UUID = Field(
        description="Subtopic to practice.",
        examples=["8f14e45f-ceea-467a-9575-000000000002"],
    )
    subtopic_name: str = Field(
        min_length=1, description="Name of the subtopic.", examples=["Regla de la potencia"]
    )
    normalized_content: str = Field(
        min_length=1,
        description="Normalized material of the subtopic (curricular anchor).",
        examples=["# Derivadas\n\nLa derivada de x^n es n·x^(n-1).\n\nEjemplo: (x²)' = 2x."],
    )
    mastery_probability: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Student's mastery; omit it for teacher requests or students without history.",
        examples=[0.35],
    )
    quantity: int = Field(
        ge=1, le=10, description="Approved exercises wanted; one run each.", examples=[1]
    )

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
