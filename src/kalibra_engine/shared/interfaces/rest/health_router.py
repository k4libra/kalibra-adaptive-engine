from typing import Literal

from fastapi import APIRouter

from kalibra_engine.shared.interfaces.rest.camel_model import CamelModel

router = APIRouter(tags=["health"])


class HealthResponse(CamelModel):
    """Liveness payload."""

    status: Literal["UP"] = "UP"


@router.get("/health")
async def health() -> HealthResponse:
    """Report that the engine process is up."""
    return HealthResponse()
