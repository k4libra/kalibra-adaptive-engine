import httpx
import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from pydantic import SecretStr

from kalibra_engine.shared.infrastructure.settings import Settings, get_settings


@pytest.mark.anyio
@pytest.mark.parametrize("mistral_enabled", [False, True])
@pytest.mark.parametrize("deepseek_enabled", [False, True])
async def test_capabilities_report_enabled_keys_without_leaks_or_provider_calls(
    app: FastAPI,
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    mistral_enabled: bool,
    deepseek_enabled: bool,
) -> None:
    mistral_key = "test-mistral-secret"
    deepseek_key = "test-deepseek-secret"
    settings = Settings(
        _env_file=None,
        mistral_api_key=SecretStr(mistral_key if mistral_enabled else ""),
        deepseek_api_key=SecretStr(deepseek_key if deepseek_enabled else ""),
    )
    app.dependency_overrides[get_settings] = lambda: settings

    async def reject_provider_call(*args: object, **kwargs: object) -> httpx.Response:
        pytest.fail("Capabilities must not call a provider.")

    local_send = client.send
    monkeypatch.setattr(httpx.AsyncClient, "send", reject_provider_call)

    # The local ASGI client must work while outbound HTTP is forbidden.
    monkeypatch.setattr(client, "send", local_send)
    response = await client.get("/api/v1/capabilities")

    assert response.status_code == 200
    assert response.json() == {
        "curricularExtraction": mistral_enabled,
        "exerciseGeneration": deepseek_enabled,
    }
    for secret in (mistral_key, deepseek_key):
        assert secret not in response.text
        assert secret not in caplog.text
