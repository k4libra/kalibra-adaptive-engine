from typing import Annotated

from fastapi import APIRouter, Depends, status

from kalibra_engine.mastery.dependencies import get_mastery_estimation_command_service
from kalibra_engine.mastery.domain.services.mastery_estimation_command_service import (
    MasteryEstimationCommandService,
)
from kalibra_engine.mastery.interfaces.rest.schemas.estimate_mastery_request import (
    EstimateMasteryRequest,
)
from kalibra_engine.mastery.interfaces.rest.schemas.mastery_estimate_response import (
    MasteryEstimateResponse,
)

router = APIRouter(prefix="/api/v1/mastery-estimates", tags=["mastery"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def estimate(
    request: EstimateMasteryRequest,
    service: Annotated[
        MasteryEstimationCommandService, Depends(get_mastery_estimation_command_service)
    ],
) -> MasteryEstimateResponse:
    """Estimate the student's mastery of a subtopic after one answer.

    Without a prior estimate the update starts from P(L0) = 0.30. The engine is
    stateless: kalibra-api (progress) stores the returned estimate.
    """
    return MasteryEstimateResponse.from_domain(service.handle(request.to_command()))
