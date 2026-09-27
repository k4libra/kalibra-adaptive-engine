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
from kalibra_engine.verification.interfaces.acl.verification_context_facade import (
    VerificationContextFacade,
)
from kalibra_engine.verification.interfaces.acl.verification_request import VerificationRequest


class ExternalVerificationService:
    """ACL to verification's open-host service (in-process): verify before delivering.

    Args:
        verification_context_facade: Verification's published facade.
    """

    def __init__(self, verification_context_facade: VerificationContextFacade) -> None:
        self._verification_context_facade = verification_context_facade

    async def verify(
        self,
        exercise: ProposedExercise,
        context: CurricularContext,
        target: DifficultyLevel,
    ) -> VerificationResult:
        """Verify a proposed exercise against the target difficulty.

        Args:
            exercise: Proposed exercise; options are sent in key order (A, B, C, D).
            context: Curricular anchor.
            target: Difficulty the exercise must have.

        Returns:
            The verdict, in generation's own terms.
        """
        summary = await self._verification_context_facade.verify(
            VerificationRequest(
                statement=exercise.statement,
                options=tuple(option.text for option in exercise.options),
                correct_option_key=exercise.correct_option_key,
                declared_difficulty=exercise.difficulty.value,
                target_difficulty=target.value,
                curricular_context=context.normalized_content,
            )
        )
        return VerificationResult(
            approved=summary.approved,
            correctness_passed=summary.correctness_passed,
            difficulty_passed=summary.difficulty_passed,
            rejection_reason=summary.rejection_reason,
            used_fallback=summary.used_fallback,
        )
