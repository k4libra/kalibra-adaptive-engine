from collections.abc import Mapping
from typing import Any

from pydantic import JsonValue

from kalibra_engine.generation.domain.services.curricular_extraction_command_service import (
    CurricularExtractionCommandService,
)
from kalibra_engine.generation.interfaces.rest.schemas.extract_content_request import (
    ExtractContentRequest,
)
from kalibra_engine.generation.interfaces.rest.schemas.extracted_content_response import (
    ExtractedContentResponse,
)


class CurricularExtractionsTaskHandler:
    """Queue entry to extraction: same contract as ``POST /api/v1/curricular-extractions``.

    Args:
        service: Curricular extraction command service.
    """

    task_type = "curricular-extractions"

    def __init__(self, service: CurricularExtractionCommandService) -> None:
        self._service = service

    async def handle(self, payload: Mapping[str, Any]) -> JsonValue:
        """Extract and normalize a curricular material.

        Args:
            payload: ``ExtractContentRequest`` body.

        Returns:
            ``ExtractedContentResponse`` body.
        """
        request = ExtractContentRequest.model_validate(payload)
        content = await self._service.handle(request.to_command())
        return ExtractedContentResponse.from_domain(content).model_dump(mode="json")
