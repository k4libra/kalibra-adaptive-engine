import re
from typing import Literal, Self

import httpx
from pydantic import BaseModel, Field, field_validator, model_validator

from kalibra_engine.generation.infrastructure.providers.deep_seek_flash_explanation_step import (
    DeepSeekFlashExplanationStep,
)
from kalibra_engine.shared.infrastructure.json_chat_completion import complete_json_chat
from kalibra_engine.shared.infrastructure.settings import Settings

_PROVIDER = "deepseek-v4-flash"
_SYSTEM_PROMPT = """\
Eres un docente universitario que diseña ejercicios de práctica de opción múltiple para \
estudiantes de ingeniería en cursos base de matemática y algoritmos. Cada ejercicio debe \
estar anclado únicamente al material curricular que se te entrega, tener una sola \
alternativa correcta y exactamente cuatro alternativas con claves A, B, C y D, y \
corresponder al nivel de dificultad solicitado (EASY, MEDIUM o HARD). Escribe en español.

El enunciado es una pregunta directa sobre el concepto, como en un examen. El estudiante \
no ve el material: nunca lo menciones ni aludas a su origen en el enunciado, las \
alternativas, los pasos ni key_idea. Prohibido usar frases como "De acuerdo con el \
material", "Según el texto", "Según el contenido", "En el contexto de la Unidad" o \
referencias al sílabo, documento, curso o unidad.

Si el enunciado incluye código, escribe el fragmento completo dentro de un único bloque \
Markdown delimitado con tres comillas invertidas y el lenguaje (por ejemplo ```cpp), con \
saltos de línea e indentación reales. Todo el código va dentro de ese bloque y nada de \
código queda fuera de él; la prosa va antes o después del bloque.

Incluye explanation_steps con entre 2 y 5 pasos ordenados. Cada paso contiene title \
(un título corto en español), detail (máximo 2 oraciones) y kind (TEXT, CODE o FORMULA). \
En TEXT, detail explica el paso en español. En CODE, detail contiene únicamente el \
fragmento de código, sin cercos Markdown. En FORMULA, detail contiene únicamente la \
fórmula en texto matemático plano, sin LaTeX ni delimitadores. Los títulos y cualquier \
prosa deben estar en español. Incluye key_idea como una sola oración en español que \
resuma el aprendizaje principal. explanation debe ser los detail de los pasos unidos \
con una línea en blanco, en el mismo orden.

Responde únicamente con un objeto JSON con esta forma exacta:
{"statement": "enunciado", \
"options": [{"key": "A", "text": "..."}, {"key": "B", "text": "..."}, \
{"key": "C", "text": "..."}, {"key": "D", "text": "..."}], \
"correct_option_key": "A", \
"explanation_steps": [{"title": "Identifica la regla", \
"detail": "Usa la regla de la potencia.", "kind": "TEXT"}, \
{"title": "Aplica la regla", "detail": "d(x^n)/dx = n*x^(n-1)", "kind": "FORMULA"}], \
"key_idea": "La regla de la potencia permite derivar potencias de x.", \
"explanation": "Usa la regla de la potencia.\\n\\nd(x^n)/dx = n*x^(n-1)", \
"difficulty": "EASY"}
"""


# Lead-in that cites the source ("De acuerdo con el material curricular sobre X, ...");
# students never see the material, so it is removed even if the model ignores the prompt.
_SOURCE_LEAD_IN = re.compile(
    r"^\s*(?:de acuerdo (?:con|a)|seg[uú]n|conforme a|con base en|bas[aá]ndote en"
    r"|tomando en cuenta|en el contexto de)\s+(?:lo que (?:indica|dice|se[nñ]ala|presenta)\s+)?"
    r"(?:el|la|los|las)\s+(?:material(?:es)?|texto|contenido|documento|s[ií]labo|unidad|lectura"
    r"|apuntes?)\b[^,?¿]*,\s*",
    re.IGNORECASE,
)


def strip_source_lead_in(statement: str) -> str:
    """Remove a leading clause that cites the curricular source and recapitalize.

    Args:
        statement: Statement proposed by the provider.

    Returns:
        The direct question; unchanged when it has no such lead-in.
    """
    direct = _SOURCE_LEAD_IN.sub("", statement, count=1)
    if direct == statement or not direct:
        return statement
    if direct.startswith("¿"):
        return "¿" + direct[1:2].upper() + direct[2:]
    return direct[:1].upper() + direct[1:]


class DeepSeekFlashOption(BaseModel):
    """Option of a draft, in the provider's own terms."""

    key: Literal["A", "B", "C", "D"]
    text: str = Field(min_length=1)


class DeepSeekFlashDraft(BaseModel):
    """Exercise draft returned by DeepSeek V4-Flash, in the provider's own terms."""

    statement: str = Field(min_length=1)
    options: list[DeepSeekFlashOption] = Field(min_length=4, max_length=4)
    correct_option_key: Literal["A", "B", "C", "D"]
    explanation: str
    explanation_steps: list[DeepSeekFlashExplanationStep] | None = Field(
        default=None, min_length=2, max_length=5
    )
    key_idea: str = ""
    difficulty: Literal["EASY", "MEDIUM", "HARD"]

    @field_validator("statement")
    @classmethod
    def _direct_statement(cls, statement: str) -> str:
        return strip_source_lead_in(statement)

    @model_validator(mode="after")
    def _keys_are_distinct(self) -> Self:
        if len({option.key for option in self.options}) != len(self.options):
            raise ValueError("option keys must be distinct")
        if self.explanation_steps is not None and not self.key_idea.strip():
            raise ValueError("structured feedback needs a key idea")
        return self


class DeepSeekFlashAdapter:
    """HTTPS adapter to DeepSeek V4-Flash, the exercise generation provider.

    Args:
        client: Shared outbound client.
        settings: Engine settings with the DeepSeek configuration.
    """

    def __init__(self, client: httpx.AsyncClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    async def propose(
        self, *, subtopic_name: str, curricular_content: str, target_difficulty: str
    ) -> DeepSeekFlashDraft:
        """Ask V4-Flash for a multiple-choice exercise anchored to the material.

        Args:
            subtopic_name: Subtopic to practice.
            curricular_content: Normalized material of the subtopic.
            target_difficulty: Required difficulty (EASY, MEDIUM or HARD).

        Returns:
            The provider's draft.

        Raises:
            ExternalProviderError: If the provider is not configured or answers badly.
            httpx.HTTPError: If the provider is unreachable or rejects the request.
        """
        user_prompt = (
            f"Subtema: {subtopic_name}\n"
            f"Nivel de dificultad solicitado: {target_difficulty}\n\n"
            f"Material curricular:\n{curricular_content}"
        )
        return await complete_json_chat(
            self._client,
            provider=_PROVIDER,
            base_url=self._settings.deepseek_base_url,
            api_key=self._settings.deepseek_api_key,
            model=self._settings.deepseek_flash_model,
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_type=DeepSeekFlashDraft,
            temperature=0.8,
            max_retries=self._settings.provider_max_retries,
        )
