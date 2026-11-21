from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class CurricularContext:
    """Curricular anchor of an exercise: the subtopic and its normalized material.

    Attributes:
        subtopic_name: Name of the subtopic.
        normalized_content: Normalized text of the subtopic material.
    """

    subtopic_name: str
    normalized_content: str
