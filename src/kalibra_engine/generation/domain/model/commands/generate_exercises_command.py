from dataclasses import dataclass
from uuid import UUID

from kalibra_engine.generation.domain.model.valueobjects.curricular_context import (
    CurricularContext,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class GenerateExercisesCommand:
    """Request to generate verified exercises for a subtopic.

    Attributes:
        course_id: Course of the subtopic.
        subtopic_id: Subtopic to practice.
        context: Curricular anchor.
        mastery_probability: Student's mastery, or None (teacher request or no history).
        quantity: Number of exercises to generate.

    Raises:
        ValueError: If ``quantity`` is lower than one.
    """

    course_id: UUID
    subtopic_id: UUID
    context: CurricularContext
    mastery_probability: float | None
    quantity: int

    def __post_init__(self) -> None:
        if self.quantity < 1:
            raise ValueError("At least one exercise must be requested.")
