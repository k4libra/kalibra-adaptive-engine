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
from kalibra_engine.shared.interfaces.rest.problem_responses import problem_response

_PATH = "/api/v1/curricular-extractions"

router = APIRouter(prefix=_PATH, tags=["Extraction"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Extract and normalize a curricular material",
    response_description="The normalized text, ready to anchor exercise generation.",
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: problem_response(
            "The material itself is unusable: unsupported format, a document the OCR "
            "provider rejects, or no extractable text. Do not retry; mark the material as "
            "an ingestion error so the teacher replaces it. A malformed request is "
            "FastAPI's validation body.",
            status=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="El material no contiene texto extraíble; reemplázalo por uno legible.",
            instance=_PATH,
            with_request_validation=True,
        ),
        status.HTTP_502_BAD_GATEWAY: problem_response(
            "Mistral OCR is unreachable, not configured (missing `MISTRAL_API_KEY`), "
            "rejects the engine's credentials or answered badly after the engine's own "
            "retries. The material is not at fault; retry later.",
            status=status.HTTP_502_BAD_GATEWAY,
            detail="Un proveedor externo de IA no respondió correctamente.",
            instance=_PATH,
        ),
    },
)
async def extract(
    request: ExtractContentRequest,
    service: Annotated[
        CurricularExtractionCommandService, Depends(get_curricular_extraction_command_service)
    ],
) -> ExtractedContentResponse:
    """Extract and normalize a curricular material.

    Mistral OCR downloads the document from `storageReference` and returns its pages;
    the engine then normalizes the text (Unicode NFC, unified line endings, no control
    characters or image placeholders, collapsed blank lines) and returns it. Nothing is
    stored: kalibra-api keeps the normalized text as the curricular anchor of the subtopic.
    """
    return ExtractedContentResponse.from_domain(await service.handle(request.to_command()))
