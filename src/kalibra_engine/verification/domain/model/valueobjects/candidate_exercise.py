from dataclasses import dataclass

from kalibra_engine.verification.domain.model.valueobjects.difficulty_level import (
    DifficultyLevel,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class CandidateExercise:
    """Exercise under verification.

    Attributes:
        statement: Exercise statement.
        options: Option texts, keyed positionally as A, B, C, D.
        correct_option_key: Key of the option declared correct.
        declared_difficulty: Difficulty declared by the generator.
        curricular_context: Curricular content the exercise must be anchored to.
    """

    statement: str
    options: tuple[str, ...]
    correct_option_key: str
    declared_difficulty: DifficultyLevel
    curricular_context: str
