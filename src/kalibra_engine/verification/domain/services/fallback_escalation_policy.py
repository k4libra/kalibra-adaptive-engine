from kalibra_engine.verification.domain.model.entities.verification_check import (
    VerificationCheck,
)
from kalibra_engine.verification.domain.model.valueobjects.check_source import CheckSource
from kalibra_engine.verification.domain.model.valueobjects.verification_criterion import (
    VerificationCriterion,
)


class FallbackEscalationPolicy:
    """Decide when the fallback provider (DeepSeek V4-Pro) must confirm a check."""

    def requires_fallback(self, check: VerificationCheck) -> bool:
        """Escalate a correctness check that the rules approved.

        Rules only prove that an exercise is well formed; whether its keyed answer is
        actually right needs the fallback provider to solve it. Failed checks are never
        escalated: they are discarded right away.

        Args:
            check: Check decided by the rules.

        Returns:
            True for a passed ``CORRECTNESS`` check decided by ``RULES``.
        """
        return (
            check.criterion is VerificationCriterion.CORRECTNESS
            and check.passed
            and check.decided_by is CheckSource.RULES
        )
