class ExternalProviderError(Exception):
    """Raised when an external AI provider returns an unusable response after retries.

    Args:
        provider: Name of the provider that failed.
        reason: Human-readable description of the failure.
    """

    def __init__(self, provider: str, reason: str) -> None:
        super().__init__(f"{provider}: {reason}")
        self.provider = provider
        self.reason = reason
