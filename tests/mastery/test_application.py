from uuid import UUID, uuid4

import pytest

from kalibra_engine.mastery.application.internal.commandservices.mastery_estimation_command_service_impl import (  # noqa: E501
    MasteryEstimationCommandServiceImpl,
)
from kalibra_engine.mastery.domain.exceptions.invalid_probability_exception import (
    InvalidProbabilityException,
)
from kalibra_engine.mastery.domain.model.commands.estimate_mastery_command import (
    EstimateMasteryCommand,
)
from kalibra_engine.mastery.domain.model.valueobjects.answer_outcome import AnswerOutcome
from kalibra_engine.mastery.domain.services.mastery_level_classifier import (
    MasteryLevelClassifier,
)
from kalibra_engine.mastery.infrastructure.config.bkt_parameters_settings import (
    BktParametersSettings,
)


def _command(prior: float | None, subtopic_id: UUID | None = None) -> EstimateMasteryCommand:
    return EstimateMasteryCommand(
        student_id=uuid4(),
        subtopic_id=subtopic_id or uuid4(),
        prior_probability=prior,
        outcome=AnswerOutcome.CORRECT,
    )


def _service(settings: BktParametersSettings) -> MasteryEstimationCommandServiceImpl:
    return MasteryEstimationCommandServiceImpl(MasteryLevelClassifier(), settings)


def test_uses_default_parameters_without_override() -> None:
    estimate = _service(BktParametersSettings()).handle(_command(None))

    assert estimate.initialized_from_base is True
    assert estimate.prior.value == 0.30


def test_subtopic_override_is_applied() -> None:
    subtopic_id = uuid4()
    settings = BktParametersSettings(subtopic_overrides={subtopic_id: {"initial_mastery": 0.5}})

    estimate = _service(settings).handle(_command(None, subtopic_id))

    assert estimate.prior.value == 0.5


def test_prior_outside_range_is_rejected() -> None:
    with pytest.raises(InvalidProbabilityException):
        _service(BktParametersSettings()).handle(_command(1.2))
