from dataclasses import dataclass

from kalibra_engine.verification.domain.model.valueobjects.verification_criterion import (
    VerificationCriterion,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class RejectionReason:
    """Why an exercise was discarded; visible to the teacher (FR-013).

    Attributes:
        criterion: Criterion that failed.
        description: Explanation in the teacher's language.
    """

    criterion: VerificationCriterion
    description: str
