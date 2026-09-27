from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class VerificationRequest:
    """Published contract: exercise to verify, in neutral types.

    Attributes:
        statement: Exercise statement.
        options: Option texts, keyed positionally as A, B, C, D.
        correct_option_key: Key of the option declared correct.
        declared_difficulty: Difficulty declared by the generator (EASY, MEDIUM, HARD).
        target_difficulty: Difficulty the exercise must have (EASY, MEDIUM, HARD).
        curricular_context: Curricular content the exercise is anchored to.
    """

    statement: str
    options: tuple[str, ...]
    correct_option_key: str
    declared_difficulty: str
    target_difficulty: str
    curricular_context: str
