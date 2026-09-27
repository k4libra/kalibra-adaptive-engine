import json

import httpx
import pytest

from kalibra_engine.generation.infrastructure.providers.deep_seek_flash_adapter import (
    DeepSeekFlashAdapter,
    DeepSeekFlashDraft,
)
from kalibra_engine.generation.infrastructure.providers.mistral_ocr_adapter import (
    MistralOcrAdapter,
)
from kalibra_engine.shared.infrastructure.external_provider_error import ExternalProviderError
from kalibra_engine.shared.infrastructure.settings import Settings

SETTINGS = Settings(deepseek_api_key="ds-key", mistral_api_key="ms-key")  # type: ignore[arg-type]

DRAFT = {
    "statement": "¿2+2?",
    "options": [{"key": k, "text": t} for k, t in zip("ABCD", "4356", strict=True)],
    "correct_option_key": "A",
    "explanation": "suma",
    "difficulty": "EASY",
}


def _chat(content: object) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(content)}}]})


@pytest.mark.anyio
async def test_flash_adapter_requests_json_exercise() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return _chat(DRAFT)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        draft = await DeepSeekFlashAdapter(client, SETTINGS).propose(
            subtopic_name="Suma", curricular_content="Aritmética.", target_difficulty="EASY"
        )

    assert draft.correct_option_key == "A"
    body = json.loads(captured[0].read())
    assert body["model"] == "deepseek-v4-flash"
    assert body["response_format"] == {"type": "json_object"}
    assert "Aritmética." in body["messages"][1]["content"]


def test_flash_draft_rejects_repeated_keys() -> None:
    repeated = {**DRAFT, "options": [{"key": "A", "text": str(i)} for i in range(4)]}
    with pytest.raises(ValueError, match="distinct"):
        DeepSeekFlashDraft.model_validate(repeated)


@pytest.mark.anyio
async def test_flash_adapter_retries_invalid_draft_then_fails() -> None:
    three_options = {**DRAFT, "options": DRAFT["options"][:3]}  # type: ignore[index]
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: _chat(three_options))
    ) as client:
        with pytest.raises(ExternalProviderError):
            await DeepSeekFlashAdapter(client, SETTINGS).propose(
                subtopic_name="s", curricular_content="c", target_difficulty="EASY"
            )


@pytest.mark.anyio
async def test_mistral_adapter_sends_document_url_and_returns_pages() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json={
                "pages": [{"markdown": "uno"}, {"markdown": "dos"}],
                "model": "m",
                "usage_info": {},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        pages = await MistralOcrAdapter(client, SETTINGS).extract(
            reference="https://files.test/m.pdf", document_type="document_url"
        )

    assert pages == ["uno", "dos"]
    request = captured[0]
    assert str(request.url) == "https://api.mistral.ai/v1/ocr"
    assert request.headers["authorization"] == "Bearer ms-key"
    assert json.loads(request.read()) == {
        "model": "mistral-ocr-latest",
        "document": {"type": "document_url", "document_url": "https://files.test/m.pdf"},
    }


@pytest.mark.anyio
async def test_mistral_adapter_rejects_unexpected_shape() -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"nope": 1}))
    ) as client:
        with pytest.raises(ExternalProviderError, match="unexpected"):
            await MistralOcrAdapter(client, SETTINGS).extract(
                reference="https://x.test/a.png", document_type="image_url"
            )


@pytest.mark.anyio
async def test_mistral_adapter_requires_api_key() -> None:
    async with httpx.AsyncClient() as client:
        with pytest.raises(ExternalProviderError, match="not configured"):
            await MistralOcrAdapter(client, Settings()).extract(
                reference="https://x.test/a.png", document_type="image_url"
            )
