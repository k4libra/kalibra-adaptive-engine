from kalibra_engine.verification.domain.model.commands.verify_exercise_command import (
    VerifyExerciseCommand,
)
from kalibra_engine.verification.domain.model.valueobjects.candidate_exercise import (
    CandidateExercise,
)
from kalibra_engine.verification.domain.model.valueobjects.difficulty_level import (
    DifficultyLevel,
)
from kalibra_engine.verification.domain.model.valueobjects.verification_criterion import (
    VerificationCriterion,
)
from kalibra_engine.verification.domain.services.exercise_verification_command_service import (
    ExerciseVerificationCommandService,
)
from kalibra_engine.verification.interfaces.acl.verification_request import VerificationRequest
from kalibra_engine.verification.interfaces.acl.verification_summary import VerificationSummary


class VerificationContextFacadeImpl:
    """Thin OHS adapter: contract to command, verification to summary.

    Args:
        command_service: Verification command service.
    """

    def __init__(self, command_service: ExerciseVerificationCommandService) -> None:
        self._command_service = command_service

    async def verify(self, request: VerificationRequest) -> VerificationSummary:
        """Verify an exercise before it is delivered.

        Args:
            request: Exercise to verify.

        Returns:
            The verdict.

        Raises:
            ValueError: If a difficulty is not EASY, MEDIUM or HARD.
        """
        command = VerifyExerciseCommand(
            candidate=CandidateExercise(
                statement=request.statement,
                options=tuple(request.options),
                correct_option_key=request.correct_option_key,
                declared_difficulty=DifficultyLevel(request.declared_difficulty),
                curricular_context=request.curricular_context,
            ),
            target_difficulty=DifficultyLevel(request.target_difficulty),
        )
        verification = await self._command_service.handle(command)
        reason = verification.rejection_reason
        return VerificationSummary(
            approved=verification.is_approved(),
            correctness_passed=verification.criterion_passed(VerificationCriterion.CORRECTNESS),
            difficulty_passed=verification.criterion_passed(VerificationCriterion.DIFFICULTY),
            rejection_reason=None if reason is None else reason.description,
            used_fallback=verification.used_fallback,
        )
