from enum import StrEnum


class DifficultyLevel(StrEnum):
    """Difficulty of an exercise (generation's own copy; no shared kernel)."""

    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
