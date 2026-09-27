from typing import Annotated

from fastapi import APIRouter, Depends, status

from kalibra_engine.generation.dependencies import get_curricular_extraction_command_service
from kalibra_engine.generation.domain.services.curricular_extraction_command_service import (
    CurricularExtractionCommandService,
)
from kalibra_engine.generation.interfaces.rest.schemas.extract_content_request import (
    ExtractContentRequest,
)
from kalibra_engine.generation.interfaces.rest.schemas.extracted_content_response import (
    ExtractedContentResponse,
)

router = APIRouter(prefix="/api/v1/curricular-extractions", tags=["generation"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def extract(
    request: ExtractContentRequest,
    service: Annotated[
        CurricularExtractionCommandService, Depends(get_curricular_extraction_command_service)
    ],
) -> ExtractedContentResponse:
    """Extract and normalize a curricular material.

    A ``422`` problem response means the material could not be extracted: curriculum
    marks it as an ingestion error so the teacher replaces it.
    """
    return ExtractedContentResponse.from_domain(await service.handle(request.to_command()))
