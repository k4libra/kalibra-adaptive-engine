from typing import Annotated

import httpx
from fastapi import Depends

from kalibra_engine.shared.infrastructure.http_client import get_http_client
from kalibra_engine.shared.infrastructure.settings import Settings, get_settings
from kalibra_engine.verification.application.acl.verification_context_facade_impl import (
    VerificationContextFacadeImpl,
)
from kalibra_engine.verification.application.internal.commandservices.exercise_verification_command_service_impl import (  # noqa: E501
    ExerciseVerificationCommandServiceImpl,
)
from kalibra_engine.verification.application.internal.outboundservices.acl.external_verification_fallback_service import (  # noqa: E501
    ExternalVerificationFallbackService,
)
from kalibra_engine.verification.domain.services.correctness_check_policy import (
    CorrectnessCheckPolicy,
)
from kalibra_engine.verification.domain.services.difficulty_check_policy import (
    DifficultyCheckPolicy,
)
from kalibra_engine.verification.domain.services.fallback_escalation_policy import (
    FallbackEscalationPolicy,
)
from kalibra_engine.verification.infrastructure.providers.deep_seek_pro_adapter import (
    DeepSeekProAdapter,
)
from kalibra_engine.verification.interfaces.acl.verification_context_facade import (
    VerificationContextFacade,
)


async def get_verification_context_facade(
    client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> VerificationContextFacade:
    """Compose the verification open-host service.

    Args:
        client: Shared outbound client.
        settings: Engine settings.

    Returns:
        The facade implementation.
    """
    command_service = ExerciseVerificationCommandServiceImpl(
        CorrectnessCheckPolicy(),
        DifficultyCheckPolicy(),
        FallbackEscalationPolicy(),
        ExternalVerificationFallbackService(DeepSeekProAdapter(client, settings)),
    )
    return VerificationContextFacadeImpl(command_service)
