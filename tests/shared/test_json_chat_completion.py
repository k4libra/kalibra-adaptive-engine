import httpx
import pytest
from pydantic import BaseModel, SecretStr

from kalibra_engine.shared.infrastructure.external_provider_error import ExternalProviderError
from kalibra_engine.shared.infrastructure.json_chat_completion import complete_json_chat


class Answer(BaseModel):
    value: int


def _completion(content: str | None) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


async def _complete(client: httpx.AsyncClient, api_key: str = "key") -> Answer:
    return await complete_json_chat(
        client,
        provider="test",
        base_url="https://llm.test/",
        api_key=SecretStr(api_key),
        model="m",
        system_prompt="Responde en JSON",
        user_prompt="u",
        response_type=Answer,
        temperature=0.0,
        max_retries=2,
    )


@pytest.mark.anyio
async def test_returns_validated_content() -> None:
    transport = httpx.MockTransport(lambda _: _completion('{"value": 7}'))
    async with httpx.AsyncClient(transport=transport) as client:
        assert await _complete(client) == Answer(value=7)


@pytest.mark.anyio
async def test_invalid_content_is_requested_again() -> None:
    responses = iter([_completion(None), _completion('{"value": 1}')])
    transport = httpx.MockTransport(lambda _: next(responses))
    async with httpx.AsyncClient(transport=transport) as client:
        assert await _complete(client) == Answer(value=1)


@pytest.mark.anyio
async def test_content_that_never_validates_is_a_provider_error() -> None:
    transport = httpx.MockTransport(lambda _: _completion('{"other": 1}'))
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(ExternalProviderError, match="expected JSON schema"):
            await _complete(client)


@pytest.mark.anyio
async def test_missing_api_key_fails_before_calling_provider() -> None:
    def fail(_: httpx.Request) -> httpx.Response:
        raise AssertionError("provider must not be called")

    async with httpx.AsyncClient(transport=httpx.MockTransport(fail)) as client:
        with pytest.raises(ExternalProviderError, match="not configured"):
            await _complete(client, api_key="")
