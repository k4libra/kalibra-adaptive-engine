from kalibra_engine.generation.domain.model.valueobjects.difficulty_level import DifficultyLevel

_EASY_UPPER_BOUND = 0.40
_MEDIUM_UPPER_BOUND = 0.70


class DifficultyTargetingPolicy:
    """Choose the exercise difficulty from the student's mastery of the subtopic."""

    def target_for(self, mastery_probability: float | None) -> DifficultyLevel:
        """Map mastery bands to difficulty: low → EASY, medium → MEDIUM, high → HARD.

        Without an estimate the student is at the base mastery P(L0) = 0.30, a low band.

        Args:
            mastery_probability: Student's mastery in [0, 1], or None.

        Returns:
            ``EASY`` below 0.40 or without estimate, ``MEDIUM`` up to 0.70, else ``HARD``.
        """
        if mastery_probability is None or mastery_probability < _EASY_UPPER_BOUND:
            return DifficultyLevel.EASY
        if mastery_probability <= _MEDIUM_UPPER_BOUND:
            return DifficultyLevel.MEDIUM
        return DifficultyLevel.HARD
