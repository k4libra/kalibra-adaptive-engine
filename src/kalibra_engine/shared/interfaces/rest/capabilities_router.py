from typing import Annotated

from fastapi import APIRouter, Depends

from kalibra_engine.shared.infrastructure.settings import Settings, get_settings
from kalibra_engine.shared.interfaces.rest.capabilities_response import CapabilitiesResponse

router = APIRouter(prefix="/api/v1/capabilities", tags=["Capabilities"])


@router.get(
    "",
    summary="Engine capabilities",
    response_description="The capabilities enabled for the internal consumer.",
)
async def get_capabilities(
    settings: Annotated[Settings, Depends(get_settings)],
) -> CapabilitiesResponse:
    """Report enabled capabilities without calling providers or exposing secrets.

    Returns:
        Availability based only on non-empty provider keys, independently of readiness.
    """
    return CapabilitiesResponse(
        curricular_extraction=bool(settings.mistral_api_key.get_secret_value()),
        exercise_generation=bool(settings.deepseek_api_key.get_secret_value()),
    )
