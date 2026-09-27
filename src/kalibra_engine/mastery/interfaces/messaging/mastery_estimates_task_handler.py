from collections.abc import Mapping
from typing import Any

from pydantic import JsonValue

from kalibra_engine.mastery.domain.services.mastery_estimation_command_service import (
    MasteryEstimationCommandService,
)
from kalibra_engine.mastery.interfaces.rest.schemas.estimate_mastery_request import (
    EstimateMasteryRequest,
)
from kalibra_engine.mastery.interfaces.rest.schemas.mastery_estimate_response import (
    MasteryEstimateResponse,
)


class MasteryEstimatesTaskHandler:
    """Queue entry to mastery: same contract as ``POST /api/v1/mastery-estimates``.

    Args:
        service: Mastery command service.
    """

    task_type = "mastery-estimates"

    def __init__(self, service: MasteryEstimationCommandService) -> None:
        self._service = service

    async def handle(self, payload: Mapping[str, Any]) -> JsonValue:
        """Estimate mastery after an answer.

        Args:
            payload: ``EstimateMasteryRequest`` body.

        Returns:
            ``MasteryEstimateResponse`` body.
        """
        request = EstimateMasteryRequest.model_validate(payload)
        estimate = self._service.handle(request.to_command())
        return MasteryEstimateResponse.from_domain(estimate).model_dump(mode="json")
