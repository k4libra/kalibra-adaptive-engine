from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from kalibra_engine.mastery.application.internal.commandservices.mastery_estimation_command_service_impl import (  # noqa: E501
    MasteryEstimationCommandServiceImpl,
)
from kalibra_engine.mastery.domain.services.mastery_estimation_command_service import (
    MasteryEstimationCommandService,
)
from kalibra_engine.mastery.domain.services.mastery_level_classifier import (
    MasteryLevelClassifier,
)
from kalibra_engine.mastery.infrastructure.config.bkt_parameters_settings import (
    BktParametersSettings,
)


@lru_cache
def get_bkt_parameters_settings() -> BktParametersSettings:
    """Return the BKT settings, read once and cached."""
    return BktParametersSettings()


async def get_mastery_estimation_command_service(
    settings: Annotated[BktParametersSettings, Depends(get_bkt_parameters_settings)],
) -> MasteryEstimationCommandService:
    """Compose the mastery command service.

    Args:
        settings: BKT settings.

    Returns:
        The command service implementation.
    """
    return MasteryEstimationCommandServiceImpl(MasteryLevelClassifier(), settings)
