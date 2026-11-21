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
from kalibra_engine.shared.interfaces.rest.problem_responses import problem_response

_PATH = "/api/v1/mastery-estimates"

router = APIRouter(prefix=_PATH, tags=["Mastery"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Estimate mastery after an answer",
    response_description="The mastery before and after the answer, and its band.",
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: problem_response(
            "The input is invalid; do not retry. A probability outside `[0, 1]` is a "
            "problem-details body; a malformed request is FastAPI's validation body.",
            status=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La probabilidad 1.4 está fuera del rango [0, 1].",
            instance=_PATH,
            with_request_validation=True,
        ),
    },
)
async def estimate(
    request: EstimateMasteryRequest,
    service: Annotated[
        MasteryEstimationCommandService, Depends(get_mastery_estimation_command_service)
    ],
) -> MasteryEstimateResponse:
    """Estimate the student's mastery of a subtopic after one answer.

    Applies one Bayesian Knowledge Tracing update with the parameters of the subtopic
    (by default P(L0) = 0.30, P(T) = 0.10, P(G) = 0.25, P(S) = 0.10). Without a prior
    estimate the update starts from P(L0).

    The engine is stateless: kalibra-api stores the returned `posterior` and sends it
    back as `priorProbability` with the next answer. It needs no AI provider, so it works
    without API keys.
    """
    return MasteryEstimateResponse.from_domain(service.handle(request.to_command()))
