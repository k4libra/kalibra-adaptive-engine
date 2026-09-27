from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TypedDict

import httpx
from fastapi import FastAPI

from kalibra_engine.shared.infrastructure.http_client import create_http_client
from kalibra_engine.shared.infrastructure.settings import get_settings


class EngineState(TypedDict):
    """Objects opened at startup and exposed to requests through ``request.state``."""

    http_client: httpx.AsyncClient


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[EngineState]:
    """Open the shared outbound HTTP client for the lifetime of the application.

    Args:
        _app: The FastAPI application (unused).

    Yields:
        The typed lifespan state.
    """
    async with create_http_client(get_settings()) as http_client:
        yield {"http_client": http_client}
