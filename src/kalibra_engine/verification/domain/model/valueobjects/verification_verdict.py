from enum import StrEnum


class VerificationVerdict(StrEnum):
    """Final decision on an exercise."""

    APPROVED = "APPROVED"
    DISCARDED = "DISCARDED"
