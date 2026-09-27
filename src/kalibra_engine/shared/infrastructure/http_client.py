import json
from collections.abc import Mapping
from typing import Any

import httpx
from fastapi import Request
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from kalibra_engine.shared.infrastructure.external_provider_error import ExternalProviderError
from kalibra_engine.shared.infrastructure.settings import Settings

_RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})


def create_http_client(settings: Settings) -> httpx.AsyncClient:
    """Build the single outbound HTTP client shared by every provider adapter.

    Args:
        settings: Engine settings with the provider timeout.

    Returns:
        A pooled ``httpx.AsyncClient``; the caller owns its lifecycle.
    """
    return httpx.AsyncClient(
        timeout=httpx.Timeout(settings.provider_timeout_seconds, connect=10.0),
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
    )


async def get_http_client(request: Request) -> httpx.AsyncClient:
    """FastAPI dependency returning the client opened by the application lifespan.

    Args:
        request: Current request, whose state carries the lifespan objects.

    Returns:
        The shared ``httpx.AsyncClient``.
    """
    client: httpx.AsyncClient = request.state.http_client
    return client


def _is_transient(error: BaseException) -> bool:
    if isinstance(error, httpx.TransportError):
        return True
    return (
        isinstance(error, httpx.HTTPStatusError)
        and error.response.status_code in _RETRYABLE_STATUS_CODES
    )


async def post_json(
    client: httpx.AsyncClient,
    url: str,
    *,
    provider: str,
    headers: Mapping[str, str],
    payload: Mapping[str, Any],
    max_retries: int,
) -> dict[str, Any]:
    """POST a JSON payload, retrying transient failures with exponential backoff.

    Only transport errors and 408/429/5xx responses are retried; any other HTTP error
    propagates immediately.

    Args:
        client: Shared outbound client.
        url: Absolute endpoint URL.
        provider: Provider name, used in error messages.
        headers: Request headers (authorization included).
        payload: JSON body.
        max_retries: Total attempts before giving up.

    Returns:
        The decoded JSON object.

    Raises:
        httpx.HTTPError: When the provider keeps failing or rejects the request.
        ExternalProviderError: When the body is not a JSON object.
    """
    retrying = AsyncRetrying(
        stop=stop_after_attempt(max_retries),
        wait=wait_exponential_jitter(initial=0.5, max=8),
        retry=retry_if_exception(_is_transient),
        reraise=True,
    )
    async for attempt in retrying:
        with attempt:
            response = await client.post(url, headers=dict(headers), json=dict(payload))
            response.raise_for_status()
            return _decode_object(response, provider)
    raise AssertionError("unreachable: tenacity re-raises the last error")


def _decode_object(response: httpx.Response, provider: str) -> dict[str, Any]:
    try:
        body = response.json()
    except json.JSONDecodeError as error:
        raise ExternalProviderError(provider, "response body is not valid JSON") from error
    if not isinstance(body, dict):
        raise ExternalProviderError(provider, "response body is not a JSON object")
    return body
