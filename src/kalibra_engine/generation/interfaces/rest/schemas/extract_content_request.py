from uuid import UUID

from pydantic import Field

from kalibra_engine.generation.domain.model.commands.extract_curricular_content_command import (
    ExtractCurricularContentCommand,
)
from kalibra_engine.generation.domain.model.valueobjects.source_document import SourceDocument
from kalibra_engine.shared.interfaces.rest.camel_model import CamelModel


class ExtractContentRequest(CamelModel):
    """Curricular extraction request sent by kalibra-api (curriculum)."""

    material_id: UUID
    storage_reference: str = Field(
        pattern=r"^https://\S+$",
        description="HTTPS URL from which the OCR provider downloads the material.",
    )
    format: str = Field(min_length=1, description="pdf, docx, pptx, png, jpg, jpeg, avif or webp.")

    def to_command(self) -> ExtractCurricularContentCommand:
        """Translate the request into the domain command.

        Returns:
            The extraction command.
        """
        return ExtractCurricularContentCommand(
            material_id=self.material_id,
            document=SourceDocument(reference=self.storage_reference, format=self.format),
        )
