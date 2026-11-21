from typing import Self

from pydantic import Field

from kalibra_engine.generation.domain.model.valueobjects.extracted_content import (
    ExtractedContent,
)
from kalibra_engine.shared.interfaces.rest.camel_model import CamelModel


class ExtractedContentResponse(CamelModel):
    """Normalized material, ready to be stored as curricular anchor."""

    normalized_text: str = Field(
        description="Normalized text of the pages that have text, separated by a blank line.",
        examples=["# Derivadas\n\nLa derivada de x^n es n·x^(n-1).\n\nEjemplo: (x²)' = 2x."],
    )
    page_count: int = Field(
        description="Pages returned by the OCR provider, empty ones included.", examples=[2]
    )

    @classmethod
    def from_domain(cls, content: ExtractedContent) -> Self:
        """Build the response from the domain content.

        Args:
            content: The extracted content.

        Returns:
            The response schema.
        """
        return cls(normalized_text=content.normalized_text, page_count=content.page_count)
