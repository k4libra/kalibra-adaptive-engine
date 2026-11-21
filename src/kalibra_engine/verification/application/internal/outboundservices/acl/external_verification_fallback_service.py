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
from kalibra_engine.verification.domain.model.valueobjects.verification_criterion import (
    VerificationCriterion,
)
from kalibra_engine.verification.infrastructure.providers.deep_seek_pro_adapter import (
    DeepSeekProAdapter,
)


class ExternalVerificationFallbackService:
    """ACL to the fallback provider: translates its review into a verification check.

    Args:
        adapter: DeepSeek V4-Pro adapter.
    """

    def __init__(self, adapter: DeepSeekProAdapter) -> None:
        self._adapter = adapter

    async def review(
        self, candidate: CandidateExercise, target: DifficultyLevel
    ) -> VerificationCheck:
        """Have the fallback provider confirm the exercise.

        The answer is confirmed only when the provider, solving on its own, picks the same
        key; a correct answer at the wrong difficulty fails the difficulty criterion.

        Args:
            candidate: Exercise under verification.
            target: Difficulty required for the student.

        Returns:
            A check decided by ``FALLBACK_PROVIDER``.

        Raises:
            ExternalProviderError: If the provider answers badly.
            httpx.HTTPError: If the provider is unreachable; the exercise is never approved.
        """
        review = await self._adapter.review(
            statement=candidate.statement,
            options=candidate.options,
            target_difficulty=target.value,
            curricular_context=candidate.curricular_context,
        )
        if review.solved_option_key != candidate.correct_option_key:
            return VerificationCheck(
                criterion=VerificationCriterion.CORRECTNESS,
                passed=False,
                detail=(
                    f"El verificador de respaldo resolvió «{review.solved_option_key}» y la "
                    f"clave marcada es «{candidate.correct_option_key}». "
                    f"{review.justification}"
                ),
                decided_by=CheckSource.FALLBACK_PROVIDER,
            )
        if not review.difficulty_matches:
            return VerificationCheck(
                criterion=VerificationCriterion.DIFFICULTY,
                passed=False,
                detail=(
                    f"El verificador de respaldo considera que no es de dificultad {target}. "
                    f"{review.justification}"
                ),
                decided_by=CheckSource.FALLBACK_PROVIDER,
            )
        return VerificationCheck(
            criterion=VerificationCriterion.CORRECTNESS,
            passed=True,
            detail=review.justification,
            decided_by=CheckSource.FALLBACK_PROVIDER,
        )
