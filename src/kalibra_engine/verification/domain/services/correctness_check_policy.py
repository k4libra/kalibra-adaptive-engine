from kalibra_engine.verification.domain.model.entities.verification_check import (
    VerificationCheck,
)
from kalibra_engine.verification.domain.model.valueobjects.candidate_exercise import (
    CandidateExercise,
)
from kalibra_engine.verification.domain.model.valueobjects.check_source import CheckSource
from kalibra_engine.verification.domain.model.valueobjects.verification_criterion import (
    VerificationCriterion,
)

OPTION_KEYS = ("A", "B", "C", "D")


class CorrectnessCheckPolicy:
    """Rule-based technical correctness of a multiple-choice exercise with four options."""

    def check(self, candidate: CandidateExercise) -> VerificationCheck:
        """Check the structural rules every well-formed exercise satisfies.

        Rules: non-empty statement, exactly four non-empty options, no repeated options
        and a correct key that points to one of the options.

        Args:
            candidate: Exercise under verification.

        Returns:
            A ``CORRECTNESS`` check decided by ``RULES``.
        """
        failures: list[str] = []
        if not candidate.statement.strip():
            failures.append("El enunciado está vacío.")
        if len(candidate.options) != len(OPTION_KEYS):
            failures.append(
                f"Debe tener {len(OPTION_KEYS)} alternativas y tiene {len(candidate.options)}."
            )
        normalized = [" ".join(option.split()).casefold() for option in candidate.options]
        if any(not option for option in normalized):
            failures.append("Hay alternativas vacías.")
        if len(set(normalized)) != len(normalized):
            failures.append("Hay alternativas repetidas.")
        if candidate.correct_option_key not in OPTION_KEYS[: len(candidate.options)]:
            failures.append(
                f"La clave correcta «{candidate.correct_option_key}» no corresponde a ninguna "
                "alternativa."
            )
        return VerificationCheck(
            criterion=VerificationCriterion.CORRECTNESS,
            passed=not failures,
            detail=" ".join(failures) or "La estructura del ejercicio es válida.",
            decided_by=CheckSource.RULES,
        )
