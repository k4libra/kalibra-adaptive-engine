from typing import Annotated

import httpx
from fastapi import Depends

from kalibra_engine.generation.application.internal.commandservices.curricular_extraction_command_service_impl import (  # noqa: E501
    CurricularExtractionCommandServiceImpl,
)
from kalibra_engine.generation.application.internal.commandservices.generation_run_command_service_impl import (  # noqa: E501
    GenerationRunCommandServiceImpl,
)
from kalibra_engine.generation.application.internal.outboundservices.acl.external_exercise_generator_service import (  # noqa: E501
    ExternalExerciseGeneratorService,
)
from kalibra_engine.generation.application.internal.outboundservices.acl.external_ocr_service import (  # noqa: E501
    ExternalOcrService,
)
from kalibra_engine.generation.application.internal.outboundservices.acl.external_verification_service import (  # noqa: E501
    ExternalVerificationService,
)
from kalibra_engine.generation.domain.services.content_normalizer import ContentNormalizer
from kalibra_engine.generation.domain.services.curricular_extraction_command_service import (
    CurricularExtractionCommandService,
)
from kalibra_engine.generation.domain.services.difficulty_targeting_policy import (
    DifficultyTargetingPolicy,
)
from kalibra_engine.generation.domain.services.generation_run_command_service import (
    GenerationRunCommandService,
)
from kalibra_engine.generation.infrastructure.providers.deep_seek_flash_adapter import (
    DeepSeekFlashAdapter,
)
from kalibra_engine.generation.infrastructure.providers.mistral_ocr_adapter import (
    MistralOcrAdapter,
)
from kalibra_engine.shared.infrastructure.http_client import get_http_client
from kalibra_engine.shared.infrastructure.settings import Settings, get_settings
from kalibra_engine.verification.dependencies import get_verification_context_facade
from kalibra_engine.verification.interfaces.acl.verification_context_facade import (
    VerificationContextFacade,
)


async def get_generation_run_command_service(
    client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
    settings: Annotated[Settings, Depends(get_settings)],
    verification_context_facade: Annotated[
        VerificationContextFacade, Depends(get_verification_context_facade)
    ],
) -> GenerationRunCommandService:
    """Compose the generation command service.

    Args:
        client: Shared outbound client.
        settings: Engine settings.
        verification_context_facade: Verification's open-host service.

    Returns:
        The command service implementation.
    """
    return GenerationRunCommandServiceImpl(
        DifficultyTargetingPolicy(),
        ExternalExerciseGeneratorService(DeepSeekFlashAdapter(client, settings)),
        ExternalVerificationService(verification_context_facade),
        max_attempts=settings.generation_max_attempts,
        max_concurrency=settings.llm_max_concurrency,
    )


async def get_curricular_extraction_command_service(
    client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CurricularExtractionCommandService:
    """Compose the curricular extraction command service.

    Args:
        client: Shared outbound client.
        settings: Engine settings.

    Returns:
        The command service implementation.
    """
    return CurricularExtractionCommandServiceImpl(
        ExternalOcrService(MistralOcrAdapter(client, settings)), ContentNormalizer()
    )
