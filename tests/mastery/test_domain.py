import math

import pytest

from kalibra_engine.mastery.domain.exceptions.invalid_probability_exception import (
    InvalidProbabilityException,
)
from kalibra_engine.mastery.domain.model.valueobjects.answer_outcome import AnswerOutcome
from kalibra_engine.mastery.domain.model.valueobjects.bkt_parameters import BktParameters
from kalibra_engine.mastery.domain.model.valueobjects.mastery_level import MasteryLevel
from kalibra_engine.mastery.domain.model.valueobjects.mastery_probability import (
    MasteryProbability,
)
from kalibra_engine.mastery.domain.services.bayesian_knowledge_tracer import (
    BayesianKnowledgeTracer,
)
from kalibra_engine.mastery.domain.services.mastery_level_classifier import (
    MasteryLevelClassifier,
)

DEFAULTS = BktParameters.defaults()


@pytest.fixture
def tracer() -> BayesianKnowledgeTracer:
    return BayesianKnowledgeTracer(MasteryLevelClassifier())


class TestMasteryProbability:
    @pytest.mark.parametrize("value", [0.0, 0.3, 1.0])
    def test_accepts_closed_unit_interval(self, value: float) -> None:
        assert MasteryProbability.of(value).value == value

    @pytest.mark.parametrize("value", [-0.01, 1.01, math.nan, math.inf])
    def test_rejects_values_outside_unit_interval(self, value: float) -> None:
        with pytest.raises(InvalidProbabilityException):
            MasteryProbability.of(value)


class TestBktParameters:
    def test_defaults_match_section_10(self) -> None:
        assert BktParameters(initial_mastery=0.30, learning=0.10, guess=0.25, slip=0.10) == DEFAULTS

    def test_rejects_invalid_parameter(self) -> None:
        with pytest.raises(InvalidProbabilityException):
            BktParameters(initial_mastery=0.3, learning=1.5, guess=0.25, slip=0.1)


class TestMasteryLevelClassifier:
    @pytest.mark.parametrize(
        ("value", "level"),
        [
            (0.0, MasteryLevel.LOW),
            (0.3999, MasteryLevel.LOW),
            (0.40, MasteryLevel.MEDIUM),
            (0.70, MasteryLevel.MEDIUM),
            (0.7001, MasteryLevel.HIGH),
            (1.0, MasteryLevel.HIGH),
        ],
    )
    def test_bands(self, value: float, level: MasteryLevel) -> None:
        assert MasteryLevelClassifier().classify(MasteryProbability.of(value)) is level


class TestBayesianKnowledgeTracer:
    def test_posterior_after_correct_answer(self, tracer: BayesianKnowledgeTracer) -> None:
        posterior = tracer.posterior_given(
            MasteryProbability.of(0.30), AnswerOutcome.CORRECT, DEFAULTS
        )
        # 0.30 * 0.90 / (0.30 * 0.90 + 0.70 * 0.25)
        assert posterior.value == pytest.approx(0.27 / 0.445)

    def test_posterior_after_incorrect_answer(self, tracer: BayesianKnowledgeTracer) -> None:
        posterior = tracer.posterior_given(
            MasteryProbability.of(0.30), AnswerOutcome.INCORRECT, DEFAULTS
        )
        # 0.30 * 0.10 / (0.30 * 0.10 + 0.70 * 0.75)
        assert posterior.value == pytest.approx(0.03 / 0.555)

    def test_learning_transition(self, tracer: BayesianKnowledgeTracer) -> None:
        learned = tracer.learn(MasteryProbability.of(0.5), DEFAULTS)
        assert learned.value == pytest.approx(0.5 + 0.5 * 0.10)

    def test_learning_never_exceeds_one(self, tracer: BayesianKnowledgeTracer) -> None:
        assert tracer.learn(MasteryProbability.of(1.0), DEFAULTS).value == 1.0

    def test_zero_probability_evidence_keeps_prior(self, tracer: BayesianKnowledgeTracer) -> None:
        no_guess = BktParameters(initial_mastery=0.3, learning=0.1, guess=0.0, slip=0.1)
        prior = MasteryProbability.of(0.0)
        assert tracer.posterior_given(prior, AnswerOutcome.CORRECT, no_guess) == prior

    def test_estimate_without_history_starts_from_base(
        self, tracer: BayesianKnowledgeTracer
    ) -> None:
        estimate = tracer.estimate(None, AnswerOutcome.CORRECT, DEFAULTS)

        assert estimate.initialized_from_base is True
        assert estimate.prior.value == 0.30
        assert estimate.posterior.value == pytest.approx(0.27 / 0.445 + (1 - 0.27 / 0.445) * 0.1)
        assert estimate.level is MasteryLevel.MEDIUM

    def test_estimate_with_history_uses_prior(self, tracer: BayesianKnowledgeTracer) -> None:
        estimate = tracer.estimate(MasteryProbability.of(0.8), AnswerOutcome.INCORRECT, DEFAULTS)

        assert estimate.initialized_from_base is False
        assert estimate.prior.value == 0.8
        assert estimate.posterior.value < 0.8

    def test_correct_answers_raise_mastery_monotonically(
        self, tracer: BayesianKnowledgeTracer
    ) -> None:
        estimate = tracer.estimate(None, AnswerOutcome.CORRECT, DEFAULTS)
        for _ in range(5):
            previous = estimate.posterior.value
            estimate = tracer.estimate(estimate.posterior, AnswerOutcome.CORRECT, DEFAULTS)
            assert estimate.posterior.value > previous
        assert estimate.level is MasteryLevel.HIGH
