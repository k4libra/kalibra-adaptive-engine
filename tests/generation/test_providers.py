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

STEPS = [
    {"title": "Identifica la suma", "detail": "Suma dos y dos.", "kind": "TEXT"},
    {"title": "Calcula el resultado", "detail": "2 + 2 = 4", "kind": "FORMULA"},
]
KEY_IDEA = "Sumar dos y dos da cuatro."


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
    prompt = body["messages"][0]["content"]
    for instruction in (
        "explanation_steps",
        "entre 2 y 5",
        "máximo 2 oraciones",
        "un título corto en español",
        "TEXT, CODE o FORMULA",
        "fragmento de código, sin cercos Markdown",
        "fórmula en texto matemático plano",
        "key_idea como una sola oración en español",
    ):
        assert instruction in prompt
    assert draft.explanation_steps is None
    assert draft.key_idea == ""


@pytest.mark.parametrize("count", [2, 5])
def test_flash_draft_accepts_structured_feedback(count: int) -> None:
    steps = (STEPS * 3)[:count]
    draft = DeepSeekFlashDraft.model_validate(
        {**DRAFT, "explanation_steps": steps, "key_idea": KEY_IDEA}
    )

    assert draft.explanation_steps is not None
    assert [step.model_dump() for step in draft.explanation_steps] == steps
    assert draft.key_idea == KEY_IDEA


@pytest.mark.parametrize("count", [0, 1, 6])
def test_flash_draft_rejects_invalid_step_count(count: int) -> None:
    with pytest.raises(ValueError):
        DeepSeekFlashDraft.model_validate(
            {**DRAFT, "explanation_steps": (STEPS * 3)[:count], "key_idea": KEY_IDEA}
        )


@pytest.mark.parametrize(
    "invalid_step",
    [
        {**STEPS[0], "kind": "HTML"},
        {**STEPS[0], "title": ""},
        {**STEPS[0], "detail": ""},
        {**STEPS[0], "title": "   "},
        {**STEPS[0], "detail": "\n "},
    ],
)
def test_flash_draft_rejects_invalid_step(invalid_step: dict[str, str]) -> None:
    with pytest.raises(ValueError):
        DeepSeekFlashDraft.model_validate(
            {**DRAFT, "explanation_steps": [invalid_step, STEPS[1]], "key_idea": KEY_IDEA}
        )


@pytest.mark.parametrize("key_idea", [None, "", "  "])
def test_flash_draft_requires_takeaway_for_structured_feedback(key_idea: str | None) -> None:
    payload = {**DRAFT, "explanation_steps": STEPS}
    if key_idea is not None:
        payload["key_idea"] = key_idea
    with pytest.raises(ValueError, match="key idea"):
        DeepSeekFlashDraft.model_validate(payload)


@pytest.mark.anyio
async def test_flash_adapter_retries_invalid_feedback() -> None:
    payloads = iter(
        [
            {**DRAFT, "explanation_steps": STEPS[:1], "key_idea": KEY_IDEA},
            {**DRAFT, "explanation_steps": STEPS, "key_idea": KEY_IDEA},
        ]
    )
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: _chat(next(payloads)))
    ) as client:
        draft = await DeepSeekFlashAdapter(client, SETTINGS).propose(
            subtopic_name="Suma", curricular_content="Aritmética.", target_difficulty="EASY"
        )

    assert draft.explanation_steps is not None
    assert len(draft.explanation_steps) == 2


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


@pytest.mark.parametrize(
    ("statement", "expected"),
    [
        (
            "De acuerdo con el material curricular sobre programación orientada a objetos, "
            "¿qué es un objeto?",
            "¿Qué es un objeto?",
        ),
        (
            "Según el material curricular, ¿qué tipo de relación define la herencia?",
            "¿Qué tipo de relación define la herencia?",
        ),
        (
            "En el contexto de la Unidad 2 (algoritmos voraces), ¿qué caracteriza a un voraz?",
            "¿Qué caracteriza a un voraz?",
        ),
        (
            "De acuerdo con el texto, la derivada de x^2 es:",
            "La derivada de x^2 es:",
        ),
    ],
)
def test_flash_draft_removes_source_lead_in_from_statement(statement: str, expected: str) -> None:
    draft = DeepSeekFlashDraft.model_validate({**DRAFT, "statement": statement})

    assert draft.statement == expected


@pytest.mark.parametrize(
    "statement",
    [
        "En el diseño orientado a objetos, ¿qué relación existe entre clase base y derivada?",
        "En el tema de archivos planos, ¿qué operación es básica?",
        "¿Cuál es el valor retornado al ejecutar misterio(5)?",
    ],
)
def test_flash_draft_keeps_direct_statements(statement: str) -> None:
    assert (
        DeepSeekFlashDraft.model_validate({**DRAFT, "statement": statement}).statement == statement
    )
