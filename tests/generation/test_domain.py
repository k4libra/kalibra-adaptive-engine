import pytest

from kalibra_engine.generation.domain.exceptions.content_extraction_failed_exception import (
    ContentExtractionFailedException,
)
from kalibra_engine.generation.domain.exceptions.generation_attempts_exhausted_exception import (
    GenerationAttemptsExhaustedException,
)
from kalibra_engine.generation.domain.model.aggregates.generation_run import GenerationRun
from kalibra_engine.generation.domain.model.valueobjects.difficulty_level import DifficultyLevel
from kalibra_engine.generation.domain.model.valueobjects.exercise_option import ExerciseOption
from kalibra_engine.generation.domain.model.valueobjects.proposed_exercise import (
    ProposedExercise,
)
from kalibra_engine.generation.domain.services.content_normalizer import ContentNormalizer
from kalibra_engine.generation.domain.services.difficulty_targeting_policy import (
    DifficultyTargetingPolicy,
)
from tests.generation.builders import CONTEXT, command, exercise, result


def _run(max_attempts: int = 3) -> GenerationRun:
    return GenerationRun.start(command(), DifficultyLevel.EASY, max_attempts=max_attempts)


class TestGenerationRun:
    def test_starts_from_command(self) -> None:
        cmd = command()
        run = GenerationRun.start(cmd, DifficultyLevel.MEDIUM)

        assert run.course_id == cmd.course_id
        assert run.subtopic_id == cmd.subtopic_id
        assert run.context == CONTEXT
        assert run.target_difficulty is DifficultyLevel.MEDIUM
        assert run.max_attempts == 3
        assert run.attempts == ()
        assert run.approved_exercise() is None
        assert run.is_exhausted() is False

    def test_discarded_then_approved(self) -> None:
        run = _run()
        run.register(exercise("rechazado"), result(approved=False))
        run.register(exercise("aprobado"), result(approved=True))

        approved = run.approved_exercise()
        assert approved is not None
        assert approved.statement == "aprobado"
        assert [attempt.number for attempt in run.attempts] == [1, 2]
        assert [attempt.exercise.statement for attempt in run.discarded_attempts()] == ["rechazado"]
        assert run.is_exhausted() is False

    def test_exhausted_after_max_rejections(self) -> None:
        run = _run(max_attempts=2)
        run.register(exercise(), result(approved=False))
        run.register(exercise(), result(approved=False))

        assert run.is_exhausted() is True
        assert run.approved_exercise() is None
        with pytest.raises(GenerationAttemptsExhaustedException):
            run.register(exercise(), result(approved=True))

    def test_no_attempt_after_approval(self) -> None:
        run = _run()
        run.register(exercise(), result(approved=True))

        with pytest.raises(ValueError, match="already has an approved"):
            run.register(exercise(), result(approved=True))

    def test_needs_at_least_one_attempt(self) -> None:
        with pytest.raises(ValueError):
            _run(max_attempts=0)


class TestValueObjects:
    def test_exercise_needs_four_distinct_keys(self) -> None:
        with pytest.raises(ValueError):
            ProposedExercise(
                statement="s",
                options=tuple(ExerciseOption(key="A", text=str(i)) for i in range(4)),
                correct_option_key="A",
                explanation="e",
                difficulty=DifficultyLevel.EASY,
            )

    def test_command_needs_positive_quantity(self) -> None:
        with pytest.raises(ValueError):
            command(quantity=0)


class TestDifficultyTargetingPolicy:
    @pytest.mark.parametrize(
        ("mastery", "difficulty"),
        [
            (None, DifficultyLevel.EASY),
            (0.0, DifficultyLevel.EASY),
            (0.3999, DifficultyLevel.EASY),
            (0.40, DifficultyLevel.MEDIUM),
            (0.70, DifficultyLevel.MEDIUM),
            (0.71, DifficultyLevel.HARD),
        ],
    )
    def test_bands(self, mastery: float | None, difficulty: DifficultyLevel) -> None:
        assert DifficultyTargetingPolicy().target_for(mastery) is difficulty


class TestContentNormalizer:
    def test_normalizes_pages(self) -> None:
        raw = "# Derivadas  \r\n\r\n\r\n\r\nx² + 1\t\x07\n![img-0.jpeg](img-0.jpeg)\fPágina 2\f   "

        content = ContentNormalizer().normalize(raw)

        assert content.normalized_text == "# Derivadas\n\nx² + 1\n\nPágina 2"
        assert content.page_count == 3

    def test_empty_material_fails(self) -> None:
        with pytest.raises(ContentExtractionFailedException):
            ContentNormalizer().normalize(" \f ![x](y) \f")
