from kalibra_engine.verification.application.internal.outboundservices.acl.external_verification_fallback_service import (  # noqa: E501
    ExternalVerificationFallbackService,
)
from kalibra_engine.verification.domain.model.aggregates.exercise_verification import (
    ExerciseVerification,
)
from kalibra_engine.verification.domain.model.commands.verify_exercise_command import (
    VerifyExerciseCommand,
)
from kalibra_engine.verification.domain.model.entities.verification_check import (
    VerificationCheck,
)
from kalibra_engine.verification.domain.model.valueobjects.rejection_reason import (
    RejectionReason,
)
from kalibra_engine.verification.domain.services.correctness_check_policy import (
    CorrectnessCheckPolicy,
)
from kalibra_engine.verification.domain.services.difficulty_check_policy import (
    DifficultyCheckPolicy,
)
from kalibra_engine.verification.domain.services.fallback_escalation_policy import (
    FallbackEscalationPolicy,
)


class ExerciseVerificationCommandServiceImpl:
    """Verify an exercise: rules first, then the fallback provider when required.

    Args:
        correctness_policy: Structural correctness rules.
        difficulty_policy: Difficulty rule.
        escalation_policy: When to ask the fallback provider.
        fallback_service: ACL to the fallback provider.
    """

    def __init__(
        self,
        correctness_policy: CorrectnessCheckPolicy,
        difficulty_policy: DifficultyCheckPolicy,
        escalation_policy: FallbackEscalationPolicy,
        fallback_service: ExternalVerificationFallbackService,
    ) -> None:
        self._correctness_policy = correctness_policy
        self._difficulty_policy = difficulty_policy
        self._escalation_policy = escalation_policy
        self._fallback_service = fallback_service

    async def handle(self, command: VerifyExerciseCommand) -> ExerciseVerification:
        """Verify the exercise and decide: any failed check discards it.

        Args:
            command: The verification request.

        Returns:
            The decided verification.

        Raises:
            ExternalProviderError: If the fallback provider answers badly.
            httpx.HTTPError: If the fallback provider is unreachable.
        """
        verification = ExerciseVerification.evaluate(command)
        correctness = self._correctness_policy.check(command.candidate)
        difficulty = self._difficulty_policy.check(command.candidate, command.target_difficulty)
        verification.record(correctness)
        verification.record(difficulty)
        if self._discard_if_failed(verification, correctness, difficulty):
            return verification

        if self._escalation_policy.requires_fallback(correctness):
            review = await self._fallback_service.review(
                command.candidate, command.target_difficulty
            )
            verification.record(review)
            if self._discard_if_failed(verification, review):
                return verification

        verification.approve()
        return verification

    @staticmethod
    def _discard_if_failed(verification: ExerciseVerification, *checks: VerificationCheck) -> bool:
        failed = next((check for check in checks if not check.passed), None)
        if failed is None:
            return False
        verification.discard(RejectionReason(criterion=failed.criterion, description=failed.detail))
        return True
