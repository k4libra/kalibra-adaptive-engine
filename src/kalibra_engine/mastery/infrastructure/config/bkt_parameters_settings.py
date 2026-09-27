from uuid import UUID

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from kalibra_engine.mastery.domain.model.valueobjects.bkt_parameters import BktParameters

_DEFAULTS = BktParameters.defaults()


class BktParametersSettings(BaseSettings):
    """BKT parameters per subtopic, read from ``BKT_*`` environment variables.

    Every subtopic uses the default parameters unless ``BKT_SUBTOPIC_OVERRIDES`` (JSON:
    ``{"<subtopic-uuid>": {"learning": 0.15}}``) overrides some of its parameters.

    Attributes:
        initial_mastery: Default P(L0).
        learning: Default P(T).
        guess: Default P(G).
        slip: Default P(S).
        subtopic_overrides: Partial parameter overrides keyed by subtopic id.
    """

    model_config = SettingsConfigDict(
        env_prefix="BKT_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    initial_mastery: float = _DEFAULTS.initial_mastery
    learning: float = _DEFAULTS.learning
    guess: float = _DEFAULTS.guess
    slip: float = _DEFAULTS.slip
    subtopic_overrides: dict[UUID, dict[str, float]] = Field(default_factory=dict)

    def parameters_for(self, subtopic_id: UUID) -> BktParameters:
        """Resolve the parameters of a subtopic.

        Args:
            subtopic_id: Subtopic identifier.

        Returns:
            Default parameters merged with the subtopic overrides, if any.
        """
        values = {
            "initial_mastery": self.initial_mastery,
            "learning": self.learning,
            "guess": self.guess,
            "slip": self.slip,
        }
        values.update(self.subtopic_overrides.get(subtopic_id, {}))
        return BktParameters(**values)
