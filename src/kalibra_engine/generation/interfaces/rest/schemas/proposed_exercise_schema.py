from typing import Literal, Self

from pydantic import Field

from kalibra_engine.generation.domain.model.valueobjects.proposed_exercise import (
    ProposedExercise,
)
from kalibra_engine.generation.interfaces.rest.schemas.explanation_step_schema import (
    ExplanationStepSchema,
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
        description="Step details joined with a blank line, in order, for compatibility.",
        examples=["Usa la regla de la potencia.\n\nd(x^3)/dx = 3*x^2"],
    )
    explanation_steps: list[ExplanationStepSchema] = Field(
        min_length=1,
        max_length=5,
        description=(
            "Two to five ordered Spanish feedback steps. A provider response missing "
            "steps yields one TEXT step containing the original explanation."
        ),
        examples=[
            [
                {
                    "title": "Identifica la regla",
                    "detail": "Usa la regla de la potencia.",
                    "kind": "TEXT",
                },
                {"title": "Deriva la potencia", "detail": "d(x^3)/dx = 3*x^2", "kind": "FORMULA"},
            ]
        ],
    )
    key_idea: str = Field(
        description="One-sentence takeaway in Spanish; empty for legacy provider responses.",
        examples=["Multiplica por el exponente y réstale uno para derivar una potencia."],
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
            explanation_steps=[
                ExplanationStepSchema(title=step.title, detail=step.detail, kind=step.kind)
                for step in exercise.explanation_steps
            ],
            key_idea=exercise.key_idea,
            difficulty=exercise.difficulty.value,
        )
