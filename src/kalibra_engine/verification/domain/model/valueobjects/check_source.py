from enum import StrEnum


class CheckSource(StrEnum):
    """Who decided a verification check."""

    RULES = "RULES"
    FALLBACK_PROVIDER = "FALLBACK_PROVIDER"
