import asyncio
from typing import Annotated, Literal

import httpx
from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import Field
from redis.asyncio import Redis
from redis.exceptions import RedisError

from kalibra_engine.shared.infrastructure.settings import Settings, get_settings
from kalibra_engine.shared.interfaces.rest.camel_model import CamelModel

router = APIRouter(prefix="/health", tags=["Health"])

_REDIS_PING_TIMEOUT_SECONDS = 2.0


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
        description=(
            "Readiness only: `httpClient`, `deepseek`, `mistral` and, when the task queue "
            "is enabled, `redis`. Empty for liveness."
        ),
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
                "At least one component is down: a provider key is missing, the HTTP "
                "client is closed, or Redis does not answer while the task queue is on."
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

    Checks that the outbound HTTP client is open, that the provider keys are configured
    and, when the task queue is enabled, that Redis answers. AI providers are not called,
    so the probe costs nothing. Responds `503` when any component is down.

    Mastery estimation needs no provider, so it keeps working while this probe reports a
    missing key.
    """
    components = {
        "httpClient": _http_client_health(getattr(request.state, "http_client", None)),
        "deepseek": _key_health(settings.deepseek_api_key.get_secret_value()),
        "mistral": _key_health(settings.mistral_api_key.get_secret_value()),
    }
    if settings.redis_enabled:
        components["redis"] = await _redis_health(getattr(request.state, "redis", None))
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


async def _redis_health(redis: "Redis | None") -> ComponentHealth:
    if redis is None:
        return ComponentHealth(status="DOWN", detail="Redis client is not open.")
    try:
        async with asyncio.timeout(_REDIS_PING_TIMEOUT_SECONDS):
            await redis.ping()
    except (RedisError, OSError, TimeoutError) as error:
        return ComponentHealth(
            status="DOWN", detail=f"Redis did not answer: {type(error).__name__}."
        )
    return ComponentHealth(status="UP")
