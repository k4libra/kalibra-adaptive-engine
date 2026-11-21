from typing import Literal, Self

from pydantic import Field

from kalibra_engine.mastery.domain.model.valueobjects.mastery_estimate import MasteryEstimate
from kalibra_engine.shared.interfaces.rest.camel_model import CamelModel


class MasteryEstimateResponse(CamelModel):
    """Updated mastery; ``posterior - prior`` is the change shown to the student."""

    prior: float = Field(
        description="Mastery before the answer; P(L0) when there was no history.",
        examples=[0.42],
    )
    posterior: float = Field(
        description="Mastery after the answer and the learning transition; store this one.",
        examples=[0.7505],
    )
    level: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        description="Band of `posterior`: low below 0.40, medium up to 0.70, high above.",
        examples=["HIGH"],
    )
    initialized_from_base: bool = Field(
        description="True when `prior` came from P(L0) because no prior was sent.",
        examples=[False],
    )

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
