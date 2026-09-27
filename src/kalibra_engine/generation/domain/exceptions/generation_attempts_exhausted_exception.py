class GenerationAttemptsExhaustedException(Exception):
    """Raised when an attempt is registered on a run that already used all its attempts.

    Args:
        max_attempts: Attempts allowed per run.
    """

    def __init__(self, max_attempts: int) -> None:
        super().__init__(
            f"La generación ya agotó sus {max_attempts} intentos sin un ejercicio aprobado."
        )
        self.max_attempts = max_attempts
