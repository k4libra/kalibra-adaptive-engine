from dataclasses import dataclass
from uuid import UUID

from kalibra_engine.generation.domain.model.valueobjects.source_document import SourceDocument


@dataclass(frozen=True, slots=True, kw_only=True)
class ExtractCurricularContentCommand:
    """Request to extract and normalize a curricular material.

    Attributes:
        material_id: Material registered by curriculum.
        document: Where and in which format the material is.
    """

    material_id: UUID
    document: SourceDocument
