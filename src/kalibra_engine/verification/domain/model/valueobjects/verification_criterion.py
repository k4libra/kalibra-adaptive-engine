from enum import StrEnum


class VerificationCriterion(StrEnum):
    """Criterion every exercise must satisfy before reaching a student."""

    CORRECTNESS = "CORRECTNESS"
    DIFFICULTY = "DIFFICULTY"
