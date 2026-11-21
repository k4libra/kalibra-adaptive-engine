import httpx

from kalibra_engine.generation.application.internal.outboundservices.acl.external_ocr_service import (  # noqa: E501
    ExternalOcrService,
)
from kalibra_engine.generation.domain.exceptions.content_extraction_failed_exception import (
    ContentExtractionFailedException,
)
from kalibra_engine.generation.domain.model.commands.extract_curricular_content_command import (
    ExtractCurricularContentCommand,
)
from kalibra_engine.generation.domain.model.valueobjects.extracted_content import (
    ExtractedContent,
)
from kalibra_engine.generation.domain.services.content_normalizer import ContentNormalizer

# Statuses with which the OCR provider rejects the document itself (bad request about the
# document, too large, unsupported media, unprocessable). Any other failure is the
# provider's or the engine's, not the material's.
_DOCUMENT_REJECTION_STATUS_CODES = frozenset({400, 413, 415, 422})


class CurricularExtractionCommandServiceImpl:
    """Extract curricular material through OCR and normalize it.

    Args:
        ocr: ACL to the OCR provider.
        normalizer: Text normalizer.
    """

    def __init__(self, ocr: ExternalOcrService, normalizer: ContentNormalizer) -> None:
        self._ocr = ocr
        self._normalizer = normalizer

    async def handle(self, command: ExtractCurricularContentCommand) -> ExtractedContent:
        """Extract and normalize the material.

        Args:
            command: The extraction request.

        Returns:
            The normalized content, ready to anchor exercises.

        Raises:
            ContentExtractionFailedException: If the material itself is unusable
                (unsupported format, rejected by the provider or without text), so
                curriculum marks it as an ingestion error and the teacher replaces it.
            ExternalProviderError: If the provider is not configured or answers badly.
            httpx.HTTPError: If the provider is unreachable, rejects the engine's
                credentials or keeps failing; the material is not at fault.
        """
        try:
            raw_text = await self._ocr.extract(command.document)
        except httpx.HTTPStatusError as error:
            if error.response.status_code not in _DOCUMENT_REJECTION_STATUS_CODES:
                raise
            raise ContentExtractionFailedException(
                "No se pudo extraer el contenido del material; verifica que el archivo sea "
                "accesible y legible, o reemplázalo."
            ) from error
        return self._normalizer.normalize(raw_text)
