from dataclasses import dataclass

from kalibra_engine.mastery.domain.model.valueobjects.mastery_level import MasteryLevel
from kalibra_engine.mastery.domain.model.valueobjects.mastery_probability import (
    MasteryProbability,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class MasteryEstimate:
    """Mastery estimate of a subtopic after one answer.

    Attributes:
        prior: Mastery before the answer (P(L0) when there was no history).
        posterior: Mastery after the answer and the learning transition.
        level: Band of ``posterior``.
        initialized_from_base: True when ``prior`` came from P(L0) instead of history.
    """

    prior: MasteryProbability
    posterior: MasteryProbability
    level: MasteryLevel
    initialized_from_base: bool
