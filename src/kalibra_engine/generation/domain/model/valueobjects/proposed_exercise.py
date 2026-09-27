from dataclasses import dataclass

from kalibra_engine.generation.domain.model.valueobjects.difficulty_level import DifficultyLevel
from kalibra_engine.generation.domain.model.valueobjects.exercise_option import ExerciseOption

OPTIONS_PER_EXERCISE = 4


@dataclass(frozen=True, slots=True, kw_only=True)
class ProposedExercise:
    """Multiple-choice exercise proposed by the generator, not yet verified.

    Attributes:
        statement: Exercise statement.
        options: Exactly four options with distinct keys, ordered by key.
        correct_option_key: Key of the option declared correct.
        explanation: Explanation of the correct answer, shown as feedback.
        difficulty: Difficulty declared by the generator.

    Raises:
        ValueError: If there are not exactly four options with distinct keys.
    """

    statement: str
    options: tuple[ExerciseOption, ...]
    correct_option_key: str
    explanation: str
    difficulty: DifficultyLevel

    def __post_init__(self) -> None:
        keys = {option.key for option in self.options}
        if len(self.options) != OPTIONS_PER_EXERCISE or len(keys) != OPTIONS_PER_EXERCISE:
            raise ValueError(
                f"An exercise needs {OPTIONS_PER_EXERCISE} options with distinct keys."
            )
