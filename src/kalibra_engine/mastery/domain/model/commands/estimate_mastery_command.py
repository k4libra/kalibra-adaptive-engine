from dataclasses import dataclass
from uuid import UUID

from kalibra_engine.mastery.domain.model.valueobjects.answer_outcome import AnswerOutcome


@dataclass(frozen=True, slots=True, kw_only=True)
class EstimateMasteryCommand:
    """Request to update a student's mastery of a subtopic after an answer.

    Attributes:
        student_id: Student who answered.
        subtopic_id: Subtopic of the exercise.
        prior_probability: Latest stored estimate, or None when there is no history.
        outcome: Whether the answer was correct.
    """

    student_id: UUID
    subtopic_id: UUID
    prior_probability: float | None
    outcome: AnswerOutcome
