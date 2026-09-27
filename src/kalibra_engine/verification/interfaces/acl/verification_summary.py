from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class VerificationSummary:
    """Published contract: verdict of a verification, in neutral types.

    Attributes:
        approved: Whether the exercise may reach a student.
        correctness_passed: Whether the latest correctness check passed.
        difficulty_passed: Whether the latest difficulty check passed.
        rejection_reason: Motive shown to the teacher; None when approved.
        used_fallback: Whether the fallback provider took part.
    """

    approved: bool
    correctness_passed: bool
    difficulty_passed: bool
    rejection_reason: str | None
    used_fallback: bool
