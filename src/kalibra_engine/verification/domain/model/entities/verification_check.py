from dataclasses import dataclass

from kalibra_engine.verification.domain.model.valueobjects.check_source import CheckSource
from kalibra_engine.verification.domain.model.valueobjects.verification_criterion import (
    VerificationCriterion,
)


@dataclass(slots=True, kw_only=True, eq=False)
class VerificationCheck:
    """Outcome of evaluating one criterion; identity-based entity of the aggregate.

    Attributes:
        criterion: Evaluated criterion.
        passed: Whether the exercise satisfies it.
        detail: Explanation of the outcome, in the teacher's language.
        decided_by: Rules or the fallback provider.
    """

    criterion: VerificationCriterion
    passed: bool
    detail: str
    decided_by: CheckSource
