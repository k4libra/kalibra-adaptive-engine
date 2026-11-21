import re
import unicodedata

from kalibra_engine.generation.domain.exceptions.content_extraction_failed_exception import (
    ContentExtractionFailedException,
)
from kalibra_engine.generation.domain.model.valueobjects.extracted_content import (
    ExtractedContent,
)

PAGE_BREAK = "\f"
_MARKDOWN_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_TRAILING_SPACES = re.compile(r"[ \t]+$", re.MULTILINE)
_EXTRA_BLANK_LINES = re.compile(r"\n{3,}")
_KEPT_CONTROL_CHARACTERS = frozenset("\n\t")


class ContentNormalizer:
    """Normalize extracted text so it can anchor exercise generation."""

    def normalize(self, raw_text: str) -> ExtractedContent:
        """Normalize raw extracted text, whose pages are separated by form feeds.

        Uses NFC (not NFKC, which would turn ``x²`` into ``x2``), unifies line endings,
        removes control characters and markdown image placeholders, trims trailing
        spaces and collapses blank lines.

        Args:
            raw_text: Extracted text; pages separated by form feed characters.

        Returns:
            The normalized text of the non-empty pages and the number of pages.

        Raises:
            ContentExtractionFailedException: If no page has text.
        """
        pages = raw_text.split(PAGE_BREAK)
        normalized_pages = [page for page in (self._normalize_page(page) for page in pages) if page]
        if not normalized_pages:
            raise ContentExtractionFailedException(
                "El material no contiene texto extraíble; reemplázalo por uno legible."
            )
        return ExtractedContent(
            normalized_text="\n\n".join(normalized_pages), page_count=len(pages)
        )

    @staticmethod
    def _normalize_page(page: str) -> str:
        text = unicodedata.normalize("NFC", page).replace("\r\n", "\n").replace("\r", "\n")
        text = _MARKDOWN_IMAGE.sub("", text)
        text = "".join(
            character
            for character in text
            if character in _KEPT_CONTROL_CHARACTERS or unicodedata.category(character) != "Cc"
        )
        text = _TRAILING_SPACES.sub("", text.expandtabs(4))
        return _EXTRA_BLANK_LINES.sub("\n\n", text).strip()
