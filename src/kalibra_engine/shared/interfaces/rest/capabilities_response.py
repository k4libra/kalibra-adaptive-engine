from pydantic import Field

from kalibra_engine.shared.interfaces.rest.camel_model import CamelModel


class CapabilitiesResponse(CamelModel):
    """Capabilities enabled for the engine's internal consumer."""

    curricular_extraction: bool = Field(
        description="Whether curricular extraction is enabled by a non-empty Mistral API key.",
        examples=[False],
    )
    exercise_generation: bool = Field(
        description="Whether exercise generation is enabled by a non-empty DeepSeek API key.",
        examples=[True],
    )
