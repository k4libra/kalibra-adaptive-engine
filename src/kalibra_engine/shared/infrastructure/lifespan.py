import logging
from collections.abc import AsyncGenerator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import TypedDict

import httpx
from fastapi import FastAPI

from kalibra_engine.shared.infrastructure.http_client import create_http_client
from kalibra_engine.shared.infrastructure.settings import Settings, get_settings

Lifespan = Callable[[FastAPI], AbstractAsyncContextManager["EngineState"]]

logger = logging.getLogger(__name__)


class EngineState(TypedDict):
    """Objects opened at startup and exposed to requests through ``request.state``."""

    http_client: httpx.AsyncClient


def build_lifespan() -> Lifespan:
    """Build the application lifespan.

    Opens the shared outbound HTTP client for the whole life of the process and warns,
    without failing, about provider keys that are not configured.

    Returns:
        The lifespan context manager factory for ``FastAPI(lifespan=...)``.
    """

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[EngineState]:
        settings = get_settings()
        _warn_about_missing_keys(settings)
        async with create_http_client(settings) as http_client:
            yield {"http_client": http_client}

    return lifespan


def _warn_about_missing_keys(settings: Settings) -> None:
    missing = {
        "DEEPSEEK_API_KEY": (settings.deepseek_api_key, "exercise generation and verification"),
        "MISTRAL_API_KEY": (settings.mistral_api_key, "curricular extraction"),
    }
    for variable, (key, capability) in missing.items():
        if not key.get_secret_value():
            logger.warning(
                "%s is not set: %s will answer 502 until it is configured.", variable, capability
            )
