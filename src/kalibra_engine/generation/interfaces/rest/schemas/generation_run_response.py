from typing import Self

from pydantic import Field

from kalibra_engine.generation.domain.model.aggregates.generation_run import GenerationRun
from kalibra_engine.generation.interfaces.rest.schemas.generation_attempt_schema import (
    GenerationAttemptSchema,
)
from kalibra_engine.generation.interfaces.rest.schemas.proposed_exercise_schema import (
    ProposedExerciseSchema,
)
from kalibra_engine.shared.interfaces.rest.camel_model import CamelModel


class GenerationRunResponse(CamelModel):
    """Result of one run: the approved exercise (if any) and every attempt."""

    approved_exercise: ProposedExerciseSchema | None = Field(
        description="The exercise that passed verification; null when the run is exhausted."
    )
    attempts: list[GenerationAttemptSchema] = Field(
        description="Every attempt of the run, approved or discarded, in order."
    )
    exhausted: bool = Field(
        description="True when every attempt was used without an approved exercise.",
        examples=[False],
    )

    @classmethod
    def from_domain(cls, run: GenerationRun) -> Self:
        """Build the response from the domain run.

        Args:
            run: A finished run.

        Returns:
            The response schema.
        """
        approved = run.approved_exercise()
        return cls(
            approved_exercise=None
            if approved is None
            else ProposedExerciseSchema.from_domain(approved),
            attempts=[GenerationAttemptSchema.from_domain(attempt) for attempt in run.attempts],
            exhausted=run.is_exhausted(),
        )
