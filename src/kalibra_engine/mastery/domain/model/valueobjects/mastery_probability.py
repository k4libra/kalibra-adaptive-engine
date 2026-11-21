import math
from dataclasses import dataclass
from typing import Self

from kalibra_engine.mastery.domain.exceptions.invalid_probability_exception import (
    InvalidProbabilityException,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class MasteryProbability:
    """Probability that the student masters a subtopic, P(L).

    Attributes:
        value: Probability in the closed interval [0, 1].

    Raises:
        InvalidProbabilityException: If ``value`` is not a finite number in [0, 1].
    """

    value: float

    def __post_init__(self) -> None:
        if not (math.isfinite(self.value) and 0.0 <= self.value <= 1.0):
            raise InvalidProbabilityException(self.value)

    @classmethod
    def of(cls, value: float) -> Self:
        """Create a probability, validating its range.

        Args:
            value: Probability in [0, 1].

        Returns:
            The value object.
        """
        return cls(value=value)
