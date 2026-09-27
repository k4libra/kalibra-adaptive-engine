class ContentExtractionFailedException(Exception):
    """Raised when a curricular material cannot be extracted or normalized.

    Args:
        reason: Explanation for the teacher, who must replace the material.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason
