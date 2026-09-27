from typing import Protocol

from kalibra_engine.generation.domain.model.commands.extract_curricular_content_command import (
    ExtractCurricularContentCommand,
)
from kalibra_engine.generation.domain.model.valueobjects.extracted_content import (
    ExtractedContent,
)


class CurricularExtractionCommandService(Protocol):
    """Command service that extracts and normalizes curricular material."""

    async def handle(self, command: ExtractCurricularContentCommand) -> ExtractedContent:
        """Extract and normalize the material.

        Args:
            command: The extraction request.

        Returns:
            The normalized content.
        """
        ...
