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
from kalibra_engine.shared.infrastructure.external_provider_error import ExternalProviderError


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
            ContentExtractionFailedException: If the material cannot be extracted, so
                curriculum marks it as an ingestion error and the teacher replaces it.
        """
        try:
            raw_text = await self._ocr.extract(command.document)
        except (httpx.HTTPError, ExternalProviderError) as error:
            raise ContentExtractionFailedException(
                "No se pudo extraer el contenido del material; verifica que el archivo sea "
                "accesible y legible, o reemplázalo."
            ) from error
        return self._normalizer.normalize(raw_text)
