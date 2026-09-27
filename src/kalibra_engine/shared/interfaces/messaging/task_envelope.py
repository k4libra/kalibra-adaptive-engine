import json
from collections.abc import Mapping
from typing import Any, Self
from uuid import UUID

from pydantic import Field

from kalibra_engine.shared.interfaces.rest.camel_model import CamelModel


class TaskEnvelope(CamelModel):
    """Task published by kalibra-api on the tasks stream.

    Stream entry fields: ``taskId`` (UUID), ``type`` (task type) and ``payload`` (JSON
    object, the same body as the REST request).
    """

    task_id: UUID
    type: str = Field(min_length=1)
    payload: dict[str, Any]

    @classmethod
    def from_fields(cls, fields: Mapping[str, str]) -> Self:
        """Parse the flat fields of a stream entry.

        Args:
            fields: Stream entry fields.

        Returns:
            The validated envelope.

        Raises:
            json.JSONDecodeError: If ``payload`` is not JSON.
            pydantic.ValidationError: If a field is missing or invalid.
        """
        raw_payload = fields.get("payload")
        return cls.model_validate(
            {
                "taskId": fields.get("taskId"),
                "type": fields.get("type"),
                "payload": None if raw_payload is None else json.loads(raw_payload),
            }
        )
