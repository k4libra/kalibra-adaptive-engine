from collections.abc import Mapping
from typing import Any, Protocol

from pydantic import JsonValue


class TaskHandler(Protocol):
    """Inbound adapter that serves one task type from the queue.

    A handler translates the task payload into its bounded context's command and the
    outcome into a JSON result, exactly as the equivalent REST endpoint does.
    """

    @property
    def task_type(self) -> str:
        """Task type served, equal to the REST resource name (e.g. ``mastery-estimates``)."""
        ...

    async def handle(self, payload: Mapping[str, Any]) -> JsonValue:
        """Execute the task.

        Args:
            payload: Task payload; same JSON body as the REST request.

        Returns:
            The result; same JSON body as the REST response.
        """
        ...
