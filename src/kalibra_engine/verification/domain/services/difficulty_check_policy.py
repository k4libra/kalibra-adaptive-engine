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


class DifficultyCheckPolicy:
    """Rule-based check that the exercise has the difficulty the student needs."""

    def check(self, candidate: CandidateExercise, target: DifficultyLevel) -> VerificationCheck:
        """Compare the declared difficulty with the target difficulty.

        Args:
            candidate: Exercise under verification.
            target: Difficulty required for the student's mastery.

        Returns:
            A ``DIFFICULTY`` check decided by ``RULES``.
        """
        passed = candidate.declared_difficulty is target
        detail = (
            f"La dificultad {target} coincide con la requerida."
            if passed
            else f"La dificultad declarada {candidate.declared_difficulty} no coincide con la "
            f"requerida {target}."
        )
        return VerificationCheck(
            criterion=VerificationCriterion.DIFFICULTY,
            passed=passed,
            detail=detail,
            decided_by=CheckSource.RULES,
        )
