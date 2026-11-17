from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True, kw_only=True)
class ExplanationStep:
    """One Spanish feedback step with a short title and typed content.

    Attributes:
        title: Short Spanish heading.
        detail: At most two sentences, a code snippet or a plain-text formula.
        kind: How the detail should be presented.
    """

    title: str
    detail: str
    kind: Literal["TEXT", "CODE", "FORMULA"]
