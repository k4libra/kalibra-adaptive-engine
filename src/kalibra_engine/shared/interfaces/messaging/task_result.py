import json
from datetime import UTC, datetime
from typing import Any, Literal, Self

from pydantic import JsonValue


class TaskResult:
    """Outcome published by the engine on the results stream.

    Stream entry fields: ``taskId``, ``type``, ``status`` (``SUCCEEDED`` or ``FAILED``),
    ``completedAt`` (ISO-8601 UTC) and either ``result`` (JSON, the same body as the REST
    response) or ``error`` (JSON, RFC 9457 problem details).

    Args:
        task_id: Identifier of the task, as received (may be empty for unreadable tasks).
        task_type: Type of the task, as received.
        status: Outcome.
        result: Result body when the task succeeded.
        error: Problem details when the task failed.
    """

    __slots__ = ("_completed_at", "_error", "_result", "_status", "_task_id", "_task_type")

    def __init__(
        self,
        *,
        task_id: str,
        task_type: str,
        status: Literal["SUCCEEDED", "FAILED"],
        result: JsonValue = None,
        error: dict[str, Any] | None = None,
    ) -> None:
        self._task_id = task_id
        self._task_type = task_type
        self._status = status
        self._result = result
        self._error = error
        self._completed_at = datetime.now(UTC)

    @classmethod
    def succeeded(cls, task_id: str, task_type: str, result: JsonValue) -> Self:
        """Build a successful outcome.

        Args:
            task_id: Identifier of the task.
            task_type: Type of the task.
            result: Result body.

        Returns:
            The outcome.
        """
        return cls(task_id=task_id, task_type=task_type, status="SUCCEEDED", result=result)

    @classmethod
    def failed(cls, task_id: str, task_type: str, error: dict[str, Any]) -> Self:
        """Build a failed outcome.

        Args:
            task_id: Identifier of the task.
            task_type: Type of the task.
            error: Problem details.

        Returns:
            The outcome.
        """
        return cls(task_id=task_id, task_type=task_type, status="FAILED", error=error)

    @property
    def status(self) -> str:
        """Outcome: ``SUCCEEDED`` or ``FAILED``."""
        return self._status

    def to_fields(self) -> dict[str, str]:
        """Serialize the outcome into flat stream entry fields.

        Returns:
            Field/value pairs ready for ``XADD``.
        """
        fields = {
            "taskId": self._task_id,
            "type": self._task_type,
            "status": self._status,
            "completedAt": self._completed_at.isoformat(),
        }
        if self._status == "SUCCEEDED":
            fields["result"] = json.dumps(self._result, ensure_ascii=False)
        else:
            fields["error"] = json.dumps(self._error, ensure_ascii=False)
        return fields
