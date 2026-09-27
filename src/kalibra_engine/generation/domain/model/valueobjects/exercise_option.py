from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class ExerciseOption:
    """One option of a multiple-choice exercise.

    Attributes:
        key: Option key (A, B, C or D).
        text: Option text.
    """

    key: str
    text: str
