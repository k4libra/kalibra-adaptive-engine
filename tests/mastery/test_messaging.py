from uuid import uuid4

import pytest
from pydantic import ValidationError

from kalibra_engine.mastery.application.internal.commandservices.mastery_estimation_command_service_impl import (  # noqa: E501
    MasteryEstimationCommandServiceImpl,
)
from kalibra_engine.mastery.domain.services.mastery_level_classifier import (
    MasteryLevelClassifier,
)
from kalibra_engine.mastery.infrastructure.config.bkt_parameters_settings import (
    BktParametersSettings,
)
from kalibra_engine.mastery.interfaces.messaging.mastery_estimates_task_handler import (
    MasteryEstimatesTaskHandler,
)


def _handler() -> MasteryEstimatesTaskHandler:
    return MasteryEstimatesTaskHandler(
        MasteryEstimationCommandServiceImpl(MasteryLevelClassifier(), BktParametersSettings())
    )


@pytest.mark.anyio
async def test_task_uses_the_rest_contract() -> None:
    result = await _handler().handle(
        {"studentId": str(uuid4()), "subtopicId": str(uuid4()), "outcome": "INCORRECT"}
    )

    assert isinstance(result, dict)
    assert set(result) == {"prior", "posterior", "level", "initializedFromBase"}
    assert result["level"] == "LOW"


@pytest.mark.anyio
async def test_invalid_payload_is_rejected() -> None:
    with pytest.raises(ValidationError):
        await _handler().handle({"outcome": "MAYBE"})
