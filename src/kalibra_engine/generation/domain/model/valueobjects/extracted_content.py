from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class ExtractedContent:
    """Normalized text of a curricular material, ready to anchor exercises.

    Attributes:
        normalized_text: Normalized text of every page.
        page_count: Number of pages processed.
    """

    normalized_text: str
    page_count: int
