from kalibra_engine.mastery.domain.model.valueobjects.mastery_level import MasteryLevel
from kalibra_engine.mastery.domain.model.valueobjects.mastery_probability import (
    MasteryProbability,
)

_LOW_UPPER_BOUND = 0.40
_MEDIUM_UPPER_BOUND = 0.70


class MasteryLevelClassifier:
    """Classify a mastery probability: low below 40 %, medium 40-70 %, high above 70 %."""

    def classify(self, probability: MasteryProbability) -> MasteryLevel:
        """Return the band of ``probability``.

        Args:
            probability: Mastery probability.

        Returns:
            ``LOW`` if < 0.40, ``MEDIUM`` if in [0.40, 0.70], ``HIGH`` if > 0.70.
        """
        if probability.value < _LOW_UPPER_BOUND:
            return MasteryLevel.LOW
        if probability.value <= _MEDIUM_UPPER_BOUND:
            return MasteryLevel.MEDIUM
        return MasteryLevel.HIGH
