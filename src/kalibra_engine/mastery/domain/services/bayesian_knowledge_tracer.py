from kalibra_engine.mastery.domain.model.valueobjects.answer_outcome import AnswerOutcome
from kalibra_engine.mastery.domain.model.valueobjects.bkt_parameters import BktParameters
from kalibra_engine.mastery.domain.model.valueobjects.mastery_estimate import MasteryEstimate
from kalibra_engine.mastery.domain.model.valueobjects.mastery_probability import (
    MasteryProbability,
)
from kalibra_engine.mastery.domain.services.mastery_level_classifier import (
    MasteryLevelClassifier,
)


class BayesianKnowledgeTracer:
    """Bayesian Knowledge Tracing update of a subtopic mastery.

    Args:
        classifier: Classifier used to band the updated estimate.
    """

    def __init__(self, classifier: MasteryLevelClassifier) -> None:
        self._classifier = classifier

    def posterior_given(
        self,
        prior: MasteryProbability,
        outcome: AnswerOutcome,
        parameters: BktParameters,
    ) -> MasteryProbability:
        """Condition the prior on the observed answer.

        Correct:   P(L)(1 - S) / [P(L)(1 - S) + (1 - P(L))G]
        Incorrect: P(L)S / [P(L)S + (1 - P(L))(1 - G)]

        Args:
            prior: Mastery before the answer, P(L).
            outcome: Observed answer.
            parameters: Subtopic parameters.

        Returns:
            P(L | answer). When the evidence has zero probability the prior is kept.
        """
        mastered, not_mastered = prior.value, 1.0 - prior.value
        if outcome is AnswerOutcome.CORRECT:
            evidence_if_mastered = mastered * (1.0 - parameters.slip)
            evidence_if_not = not_mastered * parameters.guess
        else:
            evidence_if_mastered = mastered * parameters.slip
            evidence_if_not = not_mastered * (1.0 - parameters.guess)
        evidence = evidence_if_mastered + evidence_if_not
        if evidence == 0.0:
            return prior
        return MasteryProbability.of(evidence_if_mastered / evidence)

    def learn(self, posterior: MasteryProbability, parameters: BktParameters) -> MasteryProbability:
        """Apply the learning transition P(L_t+1) = P(L | answer) + (1 - P(L | answer)) T.

        Args:
            posterior: Mastery conditioned on the answer.
            parameters: Subtopic parameters.

        Returns:
            Mastery for the next opportunity.
        """
        learned = posterior.value + (1.0 - posterior.value) * parameters.learning
        return MasteryProbability.of(min(learned, 1.0))

    def estimate(
        self,
        prior: MasteryProbability | None,
        outcome: AnswerOutcome,
        parameters: BktParameters,
    ) -> MasteryEstimate:
        """Update mastery after one answer, starting from P(L0) when there is no history.

        Args:
            prior: Latest estimate, or None for a student without history in the subtopic.
            outcome: Observed answer.
            parameters: Subtopic parameters.

        Returns:
            The prior used, the updated posterior and its band.
        """
        initialized_from_base = prior is None
        start = MasteryProbability.of(parameters.initial_mastery) if prior is None else prior
        updated = self.learn(self.posterior_given(start, outcome, parameters), parameters)
        return MasteryEstimate(
            prior=start,
            posterior=updated,
            level=self._classifier.classify(updated),
            initialized_from_base=initialized_from_base,
        )
