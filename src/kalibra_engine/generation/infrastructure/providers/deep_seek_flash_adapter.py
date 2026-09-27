from typing import Literal, Self

import httpx
from pydantic import BaseModel, Field, model_validator

from kalibra_engine.shared.infrastructure.json_chat_completion import complete_json_chat
from kalibra_engine.shared.infrastructure.settings import Settings

_PROVIDER = "deepseek-v4-flash"
_SYSTEM_PROMPT = """\
Eres un docente universitario que diseña ejercicios de práctica de opción múltiple para \
estudiantes de ingeniería en cursos base de matemática y algoritmos. Cada ejercicio debe \
estar anclado únicamente al material curricular que se te entrega, tener una sola \
alternativa correcta y exactamente cuatro alternativas con claves A, B, C y D, y \
corresponder al nivel de dificultad solicitado (EASY, MEDIUM o HARD). Escribe en español.

Responde únicamente con un objeto JSON con esta forma exacta:
{"statement": "enunciado", \
"options": [{"key": "A", "text": "..."}, {"key": "B", "text": "..."}, \
{"key": "C", "text": "..."}, {"key": "D", "text": "..."}], \
"correct_option_key": "A", "explanation": "por qué es correcta", "difficulty": "EASY"}
"""


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
    difficulty: Literal["EASY", "MEDIUM", "HARD"]

    @model_validator(mode="after")
    def _keys_are_distinct(self) -> Self:
        if len({option.key for option in self.options}) != len(self.options):
            raise ValueError("option keys must be distinct")
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
