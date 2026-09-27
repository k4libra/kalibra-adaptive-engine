from enum import StrEnum


class AnswerOutcome(StrEnum):
    """Result of the student's answer to an exercise."""

    CORRECT = "CORRECT"
    INCORRECT = "INCORRECT"
