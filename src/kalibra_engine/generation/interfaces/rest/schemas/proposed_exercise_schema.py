from typing import Literal, Self

from pydantic import Field

from kalibra_engine.generation.domain.model.valueobjects.proposed_exercise import (
    ProposedExercise,
)
from kalibra_engine.shared.interfaces.rest.camel_model import CamelModel


class ProposedExerciseSchema(CamelModel):
    """Exercise content; ``options`` are ordered by key (A, B, C, D)."""

    statement: str = Field(
        description="Exercise statement.", examples=["¿Cuál es la derivada de x³?"]
    )
    options: list[str] = Field(
        description="The four option texts, in key order (A, B, C, D).",
        examples=[["3x²", "x²", "3x", "x³/3"]],
    )
    correct_option_key: str = Field(
        description="Key of the correct option: A, B, C or D.", examples=["A"]
    )
    explanation: str = Field(
        description="Why the keyed option is correct; shown as feedback.",
        examples=["Por la regla de la potencia, la derivada de x^n es n·x^(n-1)."],
    )
    difficulty: Literal["EASY", "MEDIUM", "HARD"] = Field(
        description="Difficulty declared by the generator.", examples=["EASY"]
    )

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
