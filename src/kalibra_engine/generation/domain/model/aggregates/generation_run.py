from typing import Self
from uuid import UUID

from kalibra_engine.generation.domain.exceptions.generation_attempts_exhausted_exception import (
    GenerationAttemptsExhaustedException,
)
from kalibra_engine.generation.domain.model.commands.generate_exercises_command import (
    GenerateExercisesCommand,
)
from kalibra_engine.generation.domain.model.entities.generation_attempt import (
    GenerationAttempt,
)
from kalibra_engine.generation.domain.model.valueobjects.curricular_context import (
    CurricularContext,
)
from kalibra_engine.generation.domain.model.valueobjects.difficulty_level import DifficultyLevel
from kalibra_engine.generation.domain.model.valueobjects.proposed_exercise import (
    ProposedExercise,
)
from kalibra_engine.generation.domain.model.valueobjects.verification_result import (
    VerificationResult,
)

DEFAULT_MAX_ATTEMPTS = 3


class GenerationRun:
    """Generation of one exercise: propose, verify, discard and retry.

    A rejected exercise is never delivered; discarded attempts are kept so that
    curriculum can record them.

    Args:
        course_id: Course of the subtopic.
        subtopic_id: Subtopic to practice.
        context: Curricular anchor.
        target_difficulty: Difficulty the exercise must have.
        max_attempts: Attempts allowed before the run is exhausted.

    Raises:
        ValueError: If ``max_attempts`` is lower than one.
    """

    __slots__ = (
        "_attempts",
        "_context",
        "_course_id",
        "_max_attempts",
        "_subtopic_id",
        "_target_difficulty",
    )

    def __init__(
        self,
        *,
        course_id: UUID,
        subtopic_id: UUID,
        context: CurricularContext,
        target_difficulty: DifficultyLevel,
        max_attempts: int,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("A generation run needs at least one attempt.")
        self._course_id = course_id
        self._subtopic_id = subtopic_id
        self._context = context
        self._target_difficulty = target_difficulty
        self._max_attempts = max_attempts
        self._attempts: list[GenerationAttempt] = []

    @classmethod
    def start(
        cls,
        command: GenerateExercisesCommand,
        target: DifficultyLevel,
        *,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    ) -> Self:
        """Start a run for the command's subtopic.

        Args:
            command: The generation request.
            target: Difficulty the exercise must have.
            max_attempts: Attempts allowed before the run is exhausted.

        Returns:
            A run without attempts.
        """
        return cls(
            course_id=command.course_id,
            subtopic_id=command.subtopic_id,
            context=command.context,
            target_difficulty=target,
            max_attempts=max_attempts,
        )

    @property
    def course_id(self) -> UUID:
        """Course of the subtopic."""
        return self._course_id

    @property
    def subtopic_id(self) -> UUID:
        """Subtopic to practice."""
        return self._subtopic_id

    @property
    def context(self) -> CurricularContext:
        """Curricular anchor."""
        return self._context

    @property
    def target_difficulty(self) -> DifficultyLevel:
        """Difficulty the exercise must have."""
        return self._target_difficulty

    @property
    def max_attempts(self) -> int:
        """Attempts allowed before the run is exhausted."""
        return self._max_attempts

    @property
    def attempts(self) -> tuple[GenerationAttempt, ...]:
        """Every attempt, approved or discarded, in order."""
        return tuple(self._attempts)

    def register(self, exercise: ProposedExercise, result: VerificationResult) -> None:
        """Register a proposal and its verification verdict.

        Args:
            exercise: Proposed exercise.
            result: Verification verdict.

        Raises:
            ValueError: If the run already has an approved exercise.
            GenerationAttemptsExhaustedException: If no attempts are left.
        """
        if self.approved_exercise() is not None:
            raise ValueError("The run already has an approved exercise.")
        if len(self._attempts) >= self._max_attempts:
            raise GenerationAttemptsExhaustedException(self._max_attempts)
        self._attempts.append(
            GenerationAttempt(number=len(self._attempts) + 1, exercise=exercise, result=result)
        )

    def approved_exercise(self) -> ProposedExercise | None:
        """Return the exercise that passed verification, if any."""
        return next(
            (attempt.exercise for attempt in self._attempts if attempt.result.approved), None
        )

    def discarded_attempts(self) -> list[GenerationAttempt]:
        """Return the attempts rejected by verification."""
        return [attempt for attempt in self._attempts if not attempt.result.approved]

    def is_exhausted(self) -> bool:
        """Return whether every attempt was used without an approved exercise."""
        return len(self._attempts) >= self._max_attempts and self.approved_exercise() is None
