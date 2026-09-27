from typing import Self

from kalibra_engine.generation.domain.model.entities.generation_attempt import (
    GenerationAttempt,
)
from kalibra_engine.generation.interfaces.rest.schemas.proposed_exercise_schema import (
    ProposedExerciseSchema,
)
from kalibra_engine.shared.interfaces.rest.camel_model import CamelModel


class GenerationAttemptSchema(CamelModel):
    """One attempt and its verification verdict, for curriculum to record."""

    number: int
    exercise: ProposedExerciseSchema
    approved: bool
    correctness_passed: bool
    difficulty_passed: bool
    rejection_reason: str | None
    used_fallback: bool

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
