import asyncio

from kalibra_engine.generation.application.internal.outboundservices.acl.external_exercise_generator_service import (  # noqa: E501
    ExternalExerciseGeneratorService,
)
from kalibra_engine.generation.application.internal.outboundservices.acl.external_verification_service import (  # noqa: E501
    ExternalVerificationService,
)
from kalibra_engine.generation.domain.model.aggregates.generation_run import GenerationRun
from kalibra_engine.generation.domain.model.commands.generate_exercises_command import (
    GenerateExercisesCommand,
)
from kalibra_engine.generation.domain.services.difficulty_targeting_policy import (
    DifficultyTargetingPolicy,
)


class GenerationRunCommandServiceImpl:
    """Generate exercises and verify each one before it can be delivered.

    Args:
        targeting_policy: Chooses the difficulty from the student's mastery.
        generator: ACL to the generation provider.
        verifier: ACL to verification.
        max_attempts: Attempts per run before it is exhausted.
        max_concurrency: Runs processed at the same time (provider rate limits).
    """

    def __init__(
        self,
        targeting_policy: DifficultyTargetingPolicy,
        generator: ExternalExerciseGeneratorService,
        verifier: ExternalVerificationService,
        *,
        max_attempts: int,
        max_concurrency: int,
    ) -> None:
        self._targeting_policy = targeting_policy
        self._generator = generator
        self._verifier = verifier
        self._max_attempts = max_attempts
        self._max_concurrency = max_concurrency

    async def handle(self, command: GenerateExercisesCommand) -> list[GenerationRun]:
        """Run one generation per requested exercise, concurrently.

        Each run proposes, verifies and discards until an exercise is approved or its
        attempts are exhausted; a rejected exercise is never delivered (NFR-004).

        Args:
            command: The generation request.

        Returns:
            One finished run per requested exercise, in request order.

        Raises:
            GenerationAttemptsExhaustedException: If a run is asked for an extra attempt.
            ExternalProviderError: If a provider answers badly.
            httpx.HTTPError: If a provider is unreachable.
        """
        target = self._targeting_policy.target_for(command.mastery_probability)
        runs = [
            GenerationRun.start(command, target, max_attempts=self._max_attempts)
            for _ in range(command.quantity)
        ]
        slots = asyncio.Semaphore(self._max_concurrency)
        try:
            async with asyncio.TaskGroup() as group:
                for run in runs:
                    group.create_task(self._complete(run, slots))
        except ExceptionGroup as failures:
            raise failures.exceptions[0] from None
        return runs

    async def _complete(self, run: GenerationRun, slots: asyncio.Semaphore) -> None:
        async with slots:
            while run.approved_exercise() is None and not run.is_exhausted():
                exercise = await self._generator.propose(run.context, run.target_difficulty)
                result = await self._verifier.verify(exercise, run.context, run.target_difficulty)
                run.register(exercise, result)
