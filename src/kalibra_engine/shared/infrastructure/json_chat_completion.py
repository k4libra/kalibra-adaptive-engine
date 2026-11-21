from typing import Any

import httpx
from pydantic import BaseModel, SecretStr, ValidationError

from kalibra_engine.shared.infrastructure.external_provider_error import ExternalProviderError
from kalibra_engine.shared.infrastructure.http_client import post_json


async def complete_json_chat[ResponseT: BaseModel](
    client: httpx.AsyncClient,
    *,
    provider: str,
    base_url: str,
    api_key: SecretStr,
    model: str,
    system_prompt: str,
    user_prompt: str,
    response_type: type[ResponseT],
    temperature: float,
    max_retries: int,
) -> ResponseT:
    """Run an OpenAI-compatible chat completion in JSON mode and validate its content.

    The system prompt must ask for JSON explicitly (a DeepSeek JSON-mode requirement).
    Completions whose content does not match ``response_type`` are requested again, up
    to ``max_retries`` times.

    Args:
        client: Shared outbound client.
        provider: Provider name, used in error messages.
        base_url: API base URL, without the ``/chat/completions`` path.
        api_key: Bearer token.
        model: Model identifier.
        system_prompt: Instructions, including the expected JSON shape.
        user_prompt: Task input.
        response_type: Pydantic model that the JSON content must satisfy.
        temperature: Sampling temperature.
        max_retries: Attempts for transport failures and for invalid content.

    Returns:
        The validated completion content.

    Raises:
        ExternalProviderError: If the key is missing or the content never validates.
        httpx.HTTPError: If the provider keeps failing or rejects the request.
    """
    secret = api_key.get_secret_value()
    if not secret:
        raise ExternalProviderError(provider, "API key is not configured")
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": temperature,
        "stream": False,
    }
    last_error: Exception | None = None
    for _ in range(max_retries):
        body = await post_json(
            client,
            f"{base_url.rstrip('/')}/chat/completions",
            provider=provider,
            headers={"Authorization": f"Bearer {secret}"},
            payload=payload,
            max_retries=max_retries,
        )
        try:
            content = body["choices"][0]["message"]["content"]
            return response_type.model_validate_json(content)
        except (KeyError, IndexError, TypeError, ValidationError) as error:
            last_error = error
    raise ExternalProviderError(
        provider, "completion content did not match the expected JSON schema"
    ) from last_error
