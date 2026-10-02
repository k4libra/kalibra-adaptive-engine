import logging

import pytest

from kalibra_engine.main import create_app
from kalibra_engine.shared.infrastructure import lifespan as lifespan_module
from kalibra_engine.shared.infrastructure.settings import Settings
from tests.conftest import running

LOGGER = "kalibra_engine.shared.infrastructure.lifespan"


async def _startup_warnings(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, settings: Settings
) -> list[str]:
    monkeypatch.setattr(lifespan_module, "get_settings", lambda: settings)
    # import-linter's logging config (architecture test) disables loggers created before it.
    monkeypatch.setattr(lifespan_module.logger, "disabled", False)
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        async with running(create_app()) as http:
            assert (await http.get("/health/live")).status_code == 200
    return [record.getMessage() for record in caplog.records if record.name == LOGGER]


@pytest.mark.anyio
async def test_startup_warns_about_each_missing_key_without_failing(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    settings = Settings(deepseek_api_key="", mistral_api_key="")  # type: ignore[arg-type]

    warnings = await _startup_warnings(monkeypatch, caplog, settings)

    assert len(warnings) == 2
    assert warnings[0].startswith("DEEPSEEK_API_KEY is not set")
    assert warnings[1].startswith("MISTRAL_API_KEY is not set")


@pytest.mark.anyio
async def test_startup_warns_only_about_the_missing_key_and_never_logs_secrets(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    settings = Settings(deepseek_api_key="super-secret", mistral_api_key="")  # type: ignore[arg-type]

    warnings = await _startup_warnings(monkeypatch, caplog, settings)

    assert len(warnings) == 1
    assert warnings[0].startswith("MISTRAL_API_KEY is not set")
    assert "super-secret" not in caplog.text


@pytest.mark.anyio
async def test_startup_is_silent_when_both_keys_are_set(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    settings = Settings(deepseek_api_key="d", mistral_api_key="m")  # type: ignore[arg-type]

    assert await _startup_warnings(monkeypatch, caplog, settings) == []
