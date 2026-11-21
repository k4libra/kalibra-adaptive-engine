from typing import Self

from pydantic import Field

from kalibra_engine.generation.domain.model.entities.generation_attempt import (
    GenerationAttempt,
)
from kalibra_engine.generation.interfaces.rest.schemas.proposed_exercise_schema import (
    ProposedExerciseSchema,
)
from kalibra_engine.shared.interfaces.rest.camel_model import CamelModel


class GenerationAttemptSchema(CamelModel):
    """One attempt and its verification verdict, for curriculum to record."""

    number: int = Field(description="Position of the attempt in its run, from 1.", examples=[1])
    exercise: ProposedExerciseSchema = Field(
        description="Exercise proposed in this attempt, whether approved or discarded."
    )
    approved: bool = Field(
        description="Whether verification approved the exercise.", examples=[False]
    )
    correctness_passed: bool = Field(
        description="Whether the latest technical-correctness check passed.", examples=[False]
    )
    difficulty_passed: bool = Field(
        description="Whether the latest difficulty check passed.", examples=[True]
    )
    rejection_reason: str | None = Field(
        description="Why the exercise was discarded, for the teacher; null when approved.",
        examples=[
            "El verificador de respaldo resolvió «B» y la clave marcada es «A». "
            "La derivada de x³ es 3x²."
        ],
    )
    used_fallback: bool = Field(
        description="Whether DeepSeek V4-Pro took part in the verdict.", examples=[True]
    )

    @classmethod
    def from_domain(cls, attempt: GenerationAttempt) -> Self:
        """Build the schema from the domain attempt.

        Args:
            attempt: The attempt.

        Returns:
            The schema.
        """
        return cls(
            number=attempt.number,
            exercise=ProposedExerciseSchema.from_domain(attempt.exercise),
            approved=attempt.result.approved,
            correctness_passed=attempt.result.correctness_passed,
            difficulty_passed=attempt.result.difficulty_passed,
            rejection_reason=attempt.result.rejection_reason,
            used_fallback=attempt.result.used_fallback,
        )
