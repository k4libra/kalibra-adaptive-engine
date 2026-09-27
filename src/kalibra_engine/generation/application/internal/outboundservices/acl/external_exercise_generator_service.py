from kalibra_engine.generation.domain.model.valueobjects.curricular_context import (
    CurricularContext,
)
from kalibra_engine.generation.domain.model.valueobjects.difficulty_level import DifficultyLevel
from kalibra_engine.generation.domain.model.valueobjects.exercise_option import ExerciseOption
from kalibra_engine.generation.domain.model.valueobjects.proposed_exercise import (
    ProposedExercise,
)
from kalibra_engine.generation.infrastructure.providers.deep_seek_flash_adapter import (
    DeepSeekFlashAdapter,
)


class ExternalExerciseGeneratorService:
    """ACL to the generation provider: translates its draft into a proposed exercise.

    Args:
        adapter: DeepSeek V4-Flash adapter.
    """

    def __init__(self, adapter: DeepSeekFlashAdapter) -> None:
        self._adapter = adapter

    async def propose(
        self, context: CurricularContext, target: DifficultyLevel
    ) -> ProposedExercise:
        """Propose an exercise anchored to the context at the target difficulty.

        Args:
            context: Curricular anchor.
            target: Difficulty the exercise must have.

        Returns:
            The proposed exercise, not yet verified.

        Raises:
            ExternalProviderError: If the provider answers badly.
            httpx.HTTPError: If the provider is unreachable.
        """
        draft = await self._adapter.propose(
            subtopic_name=context.subtopic_name,
            curricular_content=context.normalized_content,
            target_difficulty=target.value,
        )
        return ProposedExercise(
            statement=draft.statement,
            options=tuple(
                ExerciseOption(key=option.key, text=option.text)
                for option in sorted(draft.options, key=lambda option: option.key)
            ),
            correct_option_key=draft.correct_option_key,
            explanation=draft.explanation,
            difficulty=DifficultyLevel(draft.difficulty),
        )
