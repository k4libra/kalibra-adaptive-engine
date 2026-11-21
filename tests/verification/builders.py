from kalibra_engine.verification.domain.model.valueobjects.candidate_exercise import (
    CandidateExercise,
)
from kalibra_engine.verification.domain.model.valueobjects.difficulty_level import (
    DifficultyLevel,
)


def candidate(**overrides: object) -> CandidateExercise:
    values: dict[str, object] = {
        "statement": "¿Cuánto es la derivada de x^2?",
        "options": ("2x", "x", "x^2", "2"),
        "correct_option_key": "A",
        "declared_difficulty": DifficultyLevel.EASY,
        "curricular_context": "Derivadas de funciones polinómicas.",
    }
    values.update(overrides)
    return CandidateExercise(**values)  # type: ignore[arg-type]
