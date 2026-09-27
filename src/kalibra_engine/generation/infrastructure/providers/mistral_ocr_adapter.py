from typing import Literal

import httpx
from pydantic import BaseModel, ValidationError

from kalibra_engine.shared.infrastructure.external_provider_error import ExternalProviderError
from kalibra_engine.shared.infrastructure.http_client import post_json
from kalibra_engine.shared.infrastructure.settings import Settings

_PROVIDER = "mistral-ocr"

MistralDocumentType = Literal["document_url", "image_url"]


class MistralOcrPage(BaseModel):
    """Page of an OCR response, in the provider's own terms."""

    markdown: str


class MistralOcrResponse(BaseModel):
    """OCR response, in the provider's own terms."""

    pages: list[MistralOcrPage]


class MistralOcrAdapter:
    """HTTPS adapter to Mistral OCR, the curricular extraction provider.

    Args:
        client: Shared outbound client.
        settings: Engine settings with the Mistral configuration.
    """

    def __init__(self, client: httpx.AsyncClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    async def extract(self, *, reference: str, document_type: MistralDocumentType) -> list[str]:
        """Run OCR over a document the provider downloads from ``reference``.

        Args:
            reference: HTTPS URL of the document.
            document_type: ``document_url`` for documents, ``image_url`` for images.

        Returns:
            The markdown of each page, in order.

        Raises:
            ExternalProviderError: If the provider is not configured or answers badly.
            httpx.HTTPError: If the provider is unreachable or rejects the request.
        """
        secret = self._settings.mistral_api_key.get_secret_value()
        if not secret:
            raise ExternalProviderError(_PROVIDER, "API key is not configured")
        body = await post_json(
            self._client,
            f"{self._settings.mistral_base_url.rstrip('/')}/v1/ocr",
            provider=_PROVIDER,
            headers={"Authorization": f"Bearer {secret}"},
            payload={
                "model": self._settings.mistral_ocr_model,
                "document": {"type": document_type, document_type: reference},
            },
            max_retries=self._settings.provider_max_retries,
        )
        try:
            response = MistralOcrResponse.model_validate(body)
        except ValidationError as error:
            raise ExternalProviderError(_PROVIDER, "unexpected OCR response shape") from error
        return [page.markdown for page in response.pages]
