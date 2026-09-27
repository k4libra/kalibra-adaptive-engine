from typing import Literal, Self

from kalibra_engine.generation.domain.model.valueobjects.proposed_exercise import (
    ProposedExercise,
)
from kalibra_engine.shared.interfaces.rest.camel_model import CamelModel


class ProposedExerciseSchema(CamelModel):
    """Exercise content; ``options`` are ordered by key (A, B, C, D)."""

    statement: str
    options: list[str]
    correct_option_key: str
    explanation: str
    difficulty: Literal["EASY", "MEDIUM", "HARD"]

    @classmethod
    def from_domain(cls, exercise: ProposedExercise) -> Self:
        """Build the schema from the domain exercise.

        Args:
            exercise: The proposed exercise.

        Returns:
            The schema.
        """
        return cls(
            statement=exercise.statement,
            options=[option.text for option in exercise.options],
            correct_option_key=exercise.correct_option_key,
            explanation=exercise.explanation,
            difficulty=exercise.difficulty.value,
        )
