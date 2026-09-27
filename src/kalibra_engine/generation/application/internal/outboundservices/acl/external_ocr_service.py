from kalibra_engine.generation.domain.exceptions.content_extraction_failed_exception import (
    ContentExtractionFailedException,
)
from kalibra_engine.generation.domain.model.valueobjects.source_document import SourceDocument
from kalibra_engine.generation.domain.services.content_normalizer import PAGE_BREAK
from kalibra_engine.generation.infrastructure.providers.mistral_ocr_adapter import (
    MistralDocumentType,
    MistralOcrAdapter,
)

_DOCUMENT_TYPE_BY_FORMAT: dict[str, MistralDocumentType] = {
    "pdf": "document_url",
    "docx": "document_url",
    "pptx": "document_url",
    "png": "image_url",
    "jpg": "image_url",
    "jpeg": "image_url",
    "avif": "image_url",
    "webp": "image_url",
}


class ExternalOcrService:
    """ACL to the OCR provider: returns the raw text of a curricular document.

    Args:
        adapter: Mistral OCR adapter.
    """

    def __init__(self, adapter: MistralOcrAdapter) -> None:
        self._adapter = adapter

    async def extract(self, document: SourceDocument) -> str:
        """Extract the raw text of the document, one form feed between pages.

        Args:
            document: Material to extract.

        Returns:
            The raw text of every page.

        Raises:
            ContentExtractionFailedException: If the format is not supported.
            ExternalProviderError: If the provider answers badly.
            httpx.HTTPError: If the provider is unreachable.
        """
        file_format = document.format.strip().lower().removeprefix(".")
        document_type = _DOCUMENT_TYPE_BY_FORMAT.get(file_format)
        if document_type is None:
            supported = ", ".join(_DOCUMENT_TYPE_BY_FORMAT)
            raise ContentExtractionFailedException(
                f"El formato «{document.format}» no está soportado; usa uno de: {supported}."
            )
        pages = await self._adapter.extract(
            reference=document.reference, document_type=document_type
        )
        return PAGE_BREAK.join(pages)
