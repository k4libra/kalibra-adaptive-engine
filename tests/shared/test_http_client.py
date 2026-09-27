import httpx
import pytest

from kalibra_engine.shared.infrastructure.external_provider_error import ExternalProviderError
from kalibra_engine.shared.infrastructure.http_client import post_json


def _client(handler: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=handler)


async def _post(client: httpx.AsyncClient, max_retries: int = 3) -> dict[str, object]:
    return await post_json(
        client,
        "https://provider.test/v1",
        provider="test",
        headers={"Authorization": "Bearer key"},
        payload={"a": 1},
        max_retries=max_retries,
    )


@pytest.mark.anyio
async def test_retries_transient_status_then_returns_body() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(503)
        return httpx.Response(200, json={"ok": True})

    async with _client(httpx.MockTransport(handler)) as client:
        body = await _post(client)

    assert body == {"ok": True}
    assert len(calls) == 2


@pytest.mark.anyio
async def test_client_error_is_not_retried() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(401)

    async with _client(httpx.MockTransport(handler)) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await _post(client)

    assert len(calls) == 1


@pytest.mark.anyio
async def test_non_object_body_is_a_provider_error() -> None:
    async with _client(httpx.MockTransport(lambda _: httpx.Response(200, json=[1]))) as client:
        with pytest.raises(ExternalProviderError):
            await _post(client)


@pytest.mark.anyio
async def test_invalid_json_is_a_provider_error() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(200, content=b"not json"))
    async with _client(transport) as client:
        with pytest.raises(ExternalProviderError):
            await _post(client)
