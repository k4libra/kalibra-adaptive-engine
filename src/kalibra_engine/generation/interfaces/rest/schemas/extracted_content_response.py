from typing import Self

from kalibra_engine.generation.domain.model.valueobjects.extracted_content import (
    ExtractedContent,
)
from kalibra_engine.shared.interfaces.rest.camel_model import CamelModel


class ExtractedContentResponse(CamelModel):
    """Normalized material, ready to be stored as curricular anchor."""

    normalized_text: str
    page_count: int

    @classmethod
    def from_domain(cls, content: ExtractedContent) -> Self:
        """Build the response from the domain content.

        Args:
            content: The extracted content.

        Returns:
            The response schema.
        """
        return cls(normalized_text=content.normalized_text, page_count=content.page_count)
