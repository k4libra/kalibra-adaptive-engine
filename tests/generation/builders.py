from uuid import uuid4

from kalibra_engine.generation.domain.model.commands.generate_exercises_command import (
    GenerateExercisesCommand,
)
from kalibra_engine.generation.domain.model.valueobjects.curricular_context import (
    CurricularContext,
)
from kalibra_engine.generation.domain.model.valueobjects.difficulty_level import DifficultyLevel
from kalibra_engine.generation.domain.model.valueobjects.exercise_option import ExerciseOption
from kalibra_engine.generation.domain.model.valueobjects.proposed_exercise import (
    ProposedExercise,
)
from kalibra_engine.generation.domain.model.valueobjects.verification_result import (
    VerificationResult,
)

CONTEXT = CurricularContext(subtopic_name="Derivadas", normalized_content="Regla de la potencia.")


def command(quantity: int = 1, mastery: float | None = None) -> GenerateExercisesCommand:
    return GenerateExercisesCommand(
        course_id=uuid4(),
        subtopic_id=uuid4(),
        context=CONTEXT,
        mastery_probability=mastery,
        quantity=quantity,
    )


def exercise(statement: str = "¿Derivada de x^2?") -> ProposedExercise:
    return ProposedExercise(
        statement=statement,
        options=tuple(
            ExerciseOption(key=key, text=text)
            for key, text in zip("ABCD", ("2x", "x", "x^2", "2"), strict=True)
        ),
        correct_option_key="A",
        explanation="Regla de la potencia.",
        difficulty=DifficultyLevel.EASY,
    )


def result(approved: bool) -> VerificationResult:
    return VerificationResult(
        approved=approved,
        correctness_passed=approved,
        difficulty_passed=True,
        rejection_reason=None if approved else "La clave marcada no es correcta.",
        used_fallback=True,
    )
