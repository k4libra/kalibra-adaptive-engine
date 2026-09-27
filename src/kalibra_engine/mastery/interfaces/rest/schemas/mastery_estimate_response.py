from typing import Literal, Self

from kalibra_engine.mastery.domain.model.valueobjects.mastery_estimate import MasteryEstimate
from kalibra_engine.shared.interfaces.rest.camel_model import CamelModel


class MasteryEstimateResponse(CamelModel):
    """Updated mastery; ``posterior - prior`` is the change shown to the student (FR-006)."""

    prior: float
    posterior: float
    level: Literal["LOW", "MEDIUM", "HIGH"]
    initialized_from_base: bool

    @classmethod
    def from_domain(cls, estimate: MasteryEstimate) -> Self:
        """Build the response from the domain estimate.

        Args:
            estimate: The domain estimate.

        Returns:
            The response schema.
        """
        return cls(
            prior=estimate.prior.value,
            posterior=estimate.posterior.value,
            level=estimate.level.value,
            initialized_from_base=estimate.initialized_from_base,
        )
