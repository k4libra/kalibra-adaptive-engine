from typing import Annotated, Literal

import httpx
from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import Field

from kalibra_engine.shared.infrastructure.settings import Settings, get_settings
from kalibra_engine.shared.interfaces.rest.camel_model import CamelModel

router = APIRouter(prefix="/health", tags=["Health"])


class ComponentHealth(CamelModel):
    """State of one dependency of the engine."""

    status: Literal["UP", "DOWN"] = Field(
        description="Whether the component is usable.", examples=["UP"]
    )
    detail: str | None = Field(
        default=None,
        description="Why the component is down; absent secrets are never echoed.",
        examples=[None],
    )


class HealthResponse(CamelModel):
    """Overall state; ``DOWN`` when any component is down."""

    status: Literal["UP", "DOWN"] = Field(
        description="`DOWN` when any component is down.", examples=["UP"]
    )
    components: dict[str, ComponentHealth] = Field(
        default_factory=dict,
        description=("Readiness only: `httpClient`, `deepseek` and `mistral`. Empty for liveness."),
        examples=[
            {
                "httpClient": {"status": "UP", "detail": None},
                "deepseek": {"status": "UP", "detail": None},
                "mistral": {"status": "UP", "detail": None},
            }
        ],
    )


@router.get(
    "/live",
    summary="Liveness probe",
    response_description="The process is up.",
)
@router.get("", include_in_schema=False)
async def live() -> HealthResponse:
    """Liveness: the process is up and serving requests.

    Used by the container health check. It checks no dependency, so it answers `UP` even
    without provider keys.
    """
    return HealthResponse(status="UP")


@router.get(
    "/ready",
    summary="Readiness probe",
    response_description="Every component is up.",
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": HealthResponse,
            "description": (
                "At least one component is down: a provider key is missing or the HTTP "
                "client is closed."
            ),
        }
    },
)
async def ready(
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthResponse:
    """Readiness: the engine can serve traffic.

    Checks that the outbound HTTP client is open and that the provider keys are
    configured. AI providers are not called, so the probe costs nothing. Responds `503`
    when any component is down.

    Mastery estimation needs no provider, so it keeps working while this probe reports a
    missing key.
    """
    components = {
        "httpClient": _http_client_health(getattr(request.state, "http_client", None)),
        "deepseek": _key_health(settings.deepseek_api_key.get_secret_value()),
        "mistral": _key_health(settings.mistral_api_key.get_secret_value()),
    }
    is_up = all(component.status == "UP" for component in components.values())
    if not is_up:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(status="UP" if is_up else "DOWN", components=components)


def _http_client_health(client: httpx.AsyncClient | None) -> ComponentHealth:
    if client is None or client.is_closed:
        return ComponentHealth(status="DOWN", detail="HTTP client is not open.")
    return ComponentHealth(status="UP")


def _key_health(api_key: str) -> ComponentHealth:
    if not api_key:
        return ComponentHealth(status="DOWN", detail="API key is not configured.")
    return ComponentHealth(status="UP")
