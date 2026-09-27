from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class VerificationResult:
    """Verdict on a proposed exercise, in generation's own terms.

    Attributes:
        approved: Whether the exercise may reach a student.
        correctness_passed: Whether it passed the correctness criterion.
        difficulty_passed: Whether it passed the difficulty criterion.
        rejection_reason: Motive shown to the teacher; None when approved.
        used_fallback: Whether the fallback provider took part.
    """

    approved: bool
    correctness_passed: bool
    difficulty_passed: bool
    rejection_reason: str | None
    used_fallback: bool
