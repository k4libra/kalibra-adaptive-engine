from typing import Literal

from pydantic import BaseModel, Field


class DeepSeekFlashExplanationStep(BaseModel):
    """Typed explanation step in the provider's own terms."""

    title: str = Field(min_length=1, pattern=r"\S")
    detail: str = Field(min_length=1, pattern=r"\S")
    kind: Literal["TEXT", "CODE", "FORMULA"]
