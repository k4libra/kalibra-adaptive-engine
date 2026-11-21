from typing import Self

from kalibra_engine.verification.domain.model.commands.verify_exercise_command import (
    VerifyExerciseCommand,
)
from kalibra_engine.verification.domain.model.entities.verification_check import (
    VerificationCheck,
)
from kalibra_engine.verification.domain.model.valueobjects.candidate_exercise import (
    CandidateExercise,
)
from kalibra_engine.verification.domain.model.valueobjects.check_source import CheckSource
from kalibra_engine.verification.domain.model.valueobjects.difficulty_level import (
    DifficultyLevel,
)
from kalibra_engine.verification.domain.model.valueobjects.rejection_reason import (
    RejectionReason,
)
from kalibra_engine.verification.domain.model.valueobjects.verification_criterion import (
    VerificationCriterion,
)
from kalibra_engine.verification.domain.model.valueobjects.verification_verdict import (
    VerificationVerdict,
)


class ExerciseVerification:
    """Verification of one exercise: records checks and reaches a single verdict.

    Every non-conforming exercise is discarded automatically, with no manual override.
    An exercise is approved only when the latest check of every criterion passed.

    Args:
        candidate: Exercise under verification.
        target_difficulty: Difficulty the exercise must have.
    """

    __slots__ = (
        "_candidate",
        "_checks",
        "_rejection_reason",
        "_target_difficulty",
        "_used_fallback",
        "_verdict",
    )

    def __init__(self, *, candidate: CandidateExercise, target_difficulty: DifficultyLevel) -> None:
        self._candidate = candidate
        self._target_difficulty = target_difficulty
        self._checks: list[VerificationCheck] = []
        self._verdict: VerificationVerdict | None = None
        self._rejection_reason: RejectionReason | None = None
        self._used_fallback = False

    @classmethod
    def evaluate(cls, command: VerifyExerciseCommand) -> Self:
        """Open the verification of the command's exercise.

        Args:
            command: The verification request.

        Returns:
            A verification without checks and without verdict.
        """
        return cls(candidate=command.candidate, target_difficulty=command.target_difficulty)

    @property
    def candidate(self) -> CandidateExercise:
        """Exercise under verification."""
        return self._candidate

    @property
    def target_difficulty(self) -> DifficultyLevel:
        """Difficulty the exercise must have."""
        return self._target_difficulty

    @property
    def checks(self) -> tuple[VerificationCheck, ...]:
        """Recorded checks, in evaluation order."""
        return tuple(self._checks)

    @property
    def verdict(self) -> VerificationVerdict | None:
        """Final decision, or None while the verification is open."""
        return self._verdict

    @property
    def rejection_reason(self) -> RejectionReason | None:
        """Why the exercise was discarded, if it was."""
        return self._rejection_reason

    @property
    def used_fallback(self) -> bool:
        """Whether the fallback provider took part in the decision."""
        return self._used_fallback

    def record(self, check: VerificationCheck) -> None:
        """Add a check to an open verification.

        Args:
            check: The evaluated check.

        Raises:
            ValueError: If the verification already has a verdict.
        """
        self._ensure_open()
        self._checks.append(check)
        if check.decided_by is CheckSource.FALLBACK_PROVIDER:
            self._used_fallback = True

    def approve(self) -> None:
        """Approve the exercise.

        Raises:
            ValueError: If there is a verdict already, or a criterion is missing or failed.
        """
        self._ensure_open()
        if not all(self.criterion_passed(criterion) for criterion in VerificationCriterion):
            raise ValueError("An exercise can only be approved when every criterion passed.")
        self._verdict = VerificationVerdict.APPROVED

    def discard(self, reason: RejectionReason) -> None:
        """Discard the exercise so it never reaches a student.

        Args:
            reason: Motive shown to the teacher.

        Raises:
            ValueError: If the verification already has a verdict.
        """
        self._ensure_open()
        self._verdict = VerificationVerdict.DISCARDED
        self._rejection_reason = reason

    def is_approved(self) -> bool:
        """Return whether the exercise was approved."""
        return self._verdict is VerificationVerdict.APPROVED

    def criterion_passed(self, criterion: VerificationCriterion) -> bool:
        """Return whether the latest check of ``criterion`` passed.

        Args:
            criterion: Criterion to inspect.

        Returns:
            False when the criterion has no check yet.
        """
        latest = next(
            (check for check in reversed(self._checks) if check.criterion is criterion), None
        )
        return latest is not None and latest.passed

    def _ensure_open(self) -> None:
        if self._verdict is not None:
            raise ValueError("The verification already has a verdict.")
