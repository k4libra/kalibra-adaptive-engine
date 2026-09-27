from collections.abc import Sequence
from typing import Literal

import httpx
from pydantic import BaseModel

from kalibra_engine.shared.infrastructure.json_chat_completion import complete_json_chat
from kalibra_engine.shared.infrastructure.settings import Settings

_PROVIDER = "deepseek-v4-pro"
_OPTION_KEYS = ("A", "B", "C", "D")
_SYSTEM_PROMPT = """\
Eres un verificador experto de ejercicios de opción múltiple de matemática y algoritmos \
para estudiantes universitarios de ingeniería. Resuelve el ejercicio por tu cuenta, sin \
suponer cuál es la respuesta marcada, y evalúa si su dificultad corresponde al nivel \
objetivo (EASY, MEDIUM o HARD) y si está anclado al contexto curricular.

Responde únicamente con un objeto JSON con esta forma exacta:
{"solved_option_key": "A", "difficulty_matches": true, "justification": "texto breve"}

- solved_option_key: la clave (A, B, C o D) de la alternativa que tú consideras correcta.
- difficulty_matches: true si la dificultad real coincide con el nivel objetivo.
- justification: explicación breve en español.
"""


class DeepSeekProReview(BaseModel):
    """Review returned by DeepSeek V4-Pro, in the provider's own terms."""

    solved_option_key: Literal["A", "B", "C", "D"]
    difficulty_matches: bool
    justification: str


class DeepSeekProAdapter:
    """HTTPS adapter to DeepSeek V4-Pro, the verification fallback provider.

    Args:
        client: Shared outbound client.
        settings: Engine settings with the DeepSeek configuration.
    """

    def __init__(self, client: httpx.AsyncClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    async def review(
        self,
        *,
        statement: str,
        options: Sequence[str],
        target_difficulty: str,
        curricular_context: str,
    ) -> DeepSeekProReview:
        """Ask V4-Pro to solve the exercise and judge its difficulty.

        The keyed answer is deliberately not sent, so the provider solves it independently.

        Args:
            statement: Exercise statement.
            options: Option texts, keyed positionally as A, B, C, D.
            target_difficulty: Required difficulty (EASY, MEDIUM or HARD).
            curricular_context: Curricular content the exercise is anchored to.

        Returns:
            The provider's review.

        Raises:
            ExternalProviderError: If the provider is not configured or answers badly.
            httpx.HTTPError: If the provider is unreachable or rejects the request.
        """
        listed_options = "\n".join(
            f"{key}) {text}" for key, text in zip(_OPTION_KEYS, options, strict=False)
        )
        user_prompt = (
            f"Contexto curricular:\n{curricular_context}\n\n"
            f"Nivel de dificultad objetivo: {target_difficulty}\n\n"
            f"Enunciado:\n{statement}\n\n"
            f"Alternativas:\n{listed_options}"
        )
        return await complete_json_chat(
            self._client,
            provider=_PROVIDER,
            base_url=self._settings.deepseek_base_url,
            api_key=self._settings.deepseek_api_key,
            model=self._settings.deepseek_pro_model,
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_type=DeepSeekProReview,
            temperature=0.0,
            max_retries=self._settings.provider_max_retries,
        )
