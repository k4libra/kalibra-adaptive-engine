import math
from dataclasses import dataclass, fields
from typing import Self

from kalibra_engine.mastery.domain.exceptions.invalid_probability_exception import (
    InvalidProbabilityException,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class BktParameters:
    """Bayesian Knowledge Tracing parameters of a subtopic.

    Attributes:
        initial_mastery: P(L0), mastery assumed before any answer.
        learning: P(T), probability of learning after each opportunity.
        guess: P(G), probability of answering right without mastery.
        slip: P(S), probability of answering wrong despite mastery.

    Raises:
        InvalidProbabilityException: If any parameter is outside [0, 1].
    """

    initial_mastery: float
    learning: float
    guess: float
    slip: float

    def __post_init__(self) -> None:
        for parameter in fields(self):
            value: float = getattr(self, parameter.name)
            if not (math.isfinite(value) and 0.0 <= value <= 1.0):
                raise InvalidProbabilityException(value)

    @classmethod
    def defaults(cls) -> Self:
        """Initial parameters from the requirements (section 10).

        P(G) = 0.25 because exercises are multiple choice with four options.

        Returns:
            P(L0) = 0.30, P(T) = 0.10, P(G) = 0.25, P(S) = 0.10.
        """
        return cls(initial_mastery=0.30, learning=0.10, guess=0.25, slip=0.10)
