from dataclasses import dataclass

from kalibra_engine.generation.domain.model.valueobjects.proposed_exercise import (
    ProposedExercise,
)
from kalibra_engine.generation.domain.model.valueobjects.verification_result import (
    VerificationResult,
)


@dataclass(slots=True, kw_only=True, eq=False)
class GenerationAttempt:
    """One proposal of a run and its verification; identity-based entity.

    Attributes:
        number: Position of the attempt in the run, starting at one.
        exercise: Proposed exercise.
        result: Verification verdict.
    """

    number: int
    exercise: ProposedExercise
    result: VerificationResult
