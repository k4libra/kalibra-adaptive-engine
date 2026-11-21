from dataclasses import dataclass

from kalibra_engine.verification.domain.model.valueobjects.candidate_exercise import (
    CandidateExercise,
)
from kalibra_engine.verification.domain.model.valueobjects.difficulty_level import (
    DifficultyLevel,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class VerifyExerciseCommand:
    """Request to verify an exercise against a target difficulty.

    Attributes:
        candidate: Exercise to verify.
        target_difficulty: Difficulty the exercise must have.
    """

    candidate: CandidateExercise
    target_difficulty: DifficultyLevel
