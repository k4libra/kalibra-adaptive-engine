class InvalidProbabilityException(Exception):
    """Raised when a probability falls outside the closed interval [0, 1].

    Args:
        value: The rejected value.
    """

    def __init__(self, value: float) -> None:
        super().__init__(f"La probabilidad {value} está fuera del rango [0, 1].")
        self.value = value
