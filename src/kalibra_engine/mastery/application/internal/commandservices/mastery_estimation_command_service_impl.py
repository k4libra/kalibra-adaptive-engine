from kalibra_engine.mastery.domain.model.commands.estimate_mastery_command import (
    EstimateMasteryCommand,
)
from kalibra_engine.mastery.domain.model.valueobjects.mastery_estimate import MasteryEstimate
from kalibra_engine.mastery.domain.model.valueobjects.mastery_probability import (
    MasteryProbability,
)
from kalibra_engine.mastery.domain.services.bayesian_knowledge_tracer import (
    BayesianKnowledgeTracer,
)
from kalibra_engine.mastery.domain.services.mastery_level_classifier import (
    MasteryLevelClassifier,
)
from kalibra_engine.mastery.infrastructure.config.bkt_parameters_settings import (
    BktParametersSettings,
)


class MasteryEstimationCommandServiceImpl:
    """Estimate mastery with BKT using the parameters configured for the subtopic.

    Args:
        classifier: Band classifier used by the tracer.
        settings: Source of the BKT parameters per subtopic.
    """

    def __init__(self, classifier: MasteryLevelClassifier, settings: BktParametersSettings) -> None:
        self._tracer = BayesianKnowledgeTracer(classifier)
        self._settings = settings

    def handle(self, command: EstimateMasteryCommand) -> MasteryEstimate:
        """Update the subtopic mastery after the student's answer.

        Args:
            command: The estimation request.

        Returns:
            The updated estimate.

        Raises:
            InvalidProbabilityException: If the prior or a parameter is outside [0, 1].
        """
        parameters = self._settings.parameters_for(command.subtopic_id)
        prior = (
            None
            if command.prior_probability is None
            else MasteryProbability.of(command.prior_probability)
        )
        return self._tracer.estimate(prior, command.outcome, parameters)
