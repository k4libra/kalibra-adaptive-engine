from typing import Literal

from pydantic import Field

from kalibra_engine.shared.interfaces.rest.camel_model import CamelModel


class ExplanationStepSchema(CamelModel):
    """One ordered feedback step with Spanish prose and typed detail."""

    title: str = Field(description="Short Spanish title of the step.", examples=["Aplica la regla"])
    detail: str = Field(
        description=(
            "At most two sentences in Spanish. CODE contains the code snippet without "
            "Markdown fences; FORMULA contains the formula in plain math text. "
            "A legacy TEXT step preserves the original explanation."
        ),
        examples=["Multiplica por el exponente y réstale uno.", "return 2 * x", "2*x^(2-1) = 2*x"],
    )
    kind: Literal["TEXT", "CODE", "FORMULA"] = Field(
        description="Presentation of detail: Spanish text, code snippet or plain-text formula.",
        examples=["TEXT", "CODE", "FORMULA"],
    )
