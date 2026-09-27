from uuid import uuid4

import pytest

from kalibra_engine.generation.domain.model.aggregates.generation_run import GenerationRun
from kalibra_engine.generation.domain.model.commands.extract_curricular_content_command import (
    ExtractCurricularContentCommand,
)
from kalibra_engine.generation.domain.model.commands.generate_exercises_command import (
    GenerateExercisesCommand,
)
from kalibra_engine.generation.domain.model.valueobjects.difficulty_level import DifficultyLevel
from kalibra_engine.generation.domain.model.valueobjects.extracted_content import (
    ExtractedContent,
)
from kalibra_engine.generation.interfaces.messaging.curricular_extractions_task_handler import (
    CurricularExtractionsTaskHandler,
)
from kalibra_engine.generation.interfaces.messaging.exercise_generations_task_handler import (
    ExerciseGenerationsTaskHandler,
)
from tests.generation.builders import exercise, result


class FakeGenerationService:
    async def handle(self, command: GenerateExercisesCommand) -> list[GenerationRun]:
        run = GenerationRun.start(command, DifficultyLevel.EASY)
        run.register(exercise(), result(approved=True))
        return [run] * command.quantity


class FakeExtractionService:
    async def handle(self, command: ExtractCurricularContentCommand) -> ExtractedContent:
        return ExtractedContent(normalized_text=command.document.format, page_count=1)


@pytest.mark.anyio
async def test_generation_task_returns_the_rest_list_contract() -> None:
    runs = await ExerciseGenerationsTaskHandler(FakeGenerationService()).handle(
        {
            "courseId": str(uuid4()),
            "subtopicId": str(uuid4()),
            "subtopicName": "Derivadas",
            "normalizedContent": "x",
            "quantity": 2,
        }
    )

    assert isinstance(runs, list)
    assert len(runs) == 2
    assert runs[0]["exhausted"] is False  # type: ignore[index,call-overload]
    assert runs[0]["approvedExercise"]["correctOptionKey"] == "A"  # type: ignore[index,call-overload]


@pytest.mark.anyio
async def test_extraction_task_returns_the_rest_contract() -> None:
    content = await CurricularExtractionsTaskHandler(FakeExtractionService()).handle(
        {"materialId": str(uuid4()), "storageReference": "https://x.test/a.pdf", "format": "pdf"}
    )

    assert content == {"normalizedText": "pdf", "pageCount": 1}
