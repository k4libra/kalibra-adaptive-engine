from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceDocument:
    """Curricular material to extract.

    Attributes:
        reference: HTTPS URL where the provider can read the document.
        format: File format (pdf, docx, pptx, png, jpg, jpeg, avif, webp).
    """

    reference: str
    format: str
