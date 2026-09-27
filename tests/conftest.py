from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from starlette.types import Receive, Scope, Send

from kalibra_engine.main import create_app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def app() -> FastAPI:
    return create_app()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


@asynccontextmanager
async def running(app: FastAPI) -> AsyncGenerator[AsyncClient]:
    """Run the application lifespan and serve requests with its state.

    ``ASGITransport`` does not drive the ASGI lifespan, so this runs the app's own
    lifespan and hands its state to every request, as a server would.
    """
    async with app.router.lifespan_context(app) as state:

        async def with_lifespan_state(scope: Scope, receive: Receive, send: Send) -> None:
            scope["state"] = dict(state or {})
            await app(scope, receive, send)

        transport = ASGITransport(app=with_lifespan_state)
        async with AsyncClient(transport=transport, base_url="http://test") as http:
            yield http
