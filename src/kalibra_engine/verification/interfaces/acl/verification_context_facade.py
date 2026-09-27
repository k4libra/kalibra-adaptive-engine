from typing import Protocol

from kalibra_engine.verification.interfaces.acl.verification_request import VerificationRequest
from kalibra_engine.verification.interfaces.acl.verification_summary import VerificationSummary


class VerificationContextFacade(Protocol):
    """Open-host service of verification: the only in-process entry to this context."""

    async def verify(self, request: VerificationRequest) -> VerificationSummary:
        """Verify an exercise before it is delivered.

        Args:
            request: Exercise to verify.

        Returns:
            The verdict; a non-approved exercise must never reach a student.
        """
        ...
