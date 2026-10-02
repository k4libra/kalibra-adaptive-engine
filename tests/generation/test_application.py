import asyncio
from uuid import uuid4

import httpx
import pytest

from kalibra_engine.generation.application.internal.commandservices.curricular_extraction_command_service_impl import (  # noqa: E501
    CurricularExtractionCommandServiceImpl,
)
from kalibra_engine.generation.application.internal.commandservices.generation_run_command_service_impl import (  # noqa: E501
    GenerationRunCommandServiceImpl,
)
from kalibra_engine.generation.application.internal.outboundservices.acl.external_exercise_generator_service import (  # noqa: E501
    ExternalExerciseGeneratorService,
)
from kalibra_engine.generation.application.internal.outboundservices.acl.external_ocr_service import (  # noqa: E501
    ExternalOcrService,
)
from kalibra_engine.generation.application.internal.outboundservices.acl.external_verification_service import (  # noqa: E501
    ExternalVerificationService,
)
from kalibra_engine.generation.domain.exceptions.content_extraction_failed_exception import (
    ContentExtractionFailedException,
)
from kalibra_engine.generation.domain.model.commands.extract_curricular_content_command import (
    ExtractCurricularContentCommand,
)
from kalibra_engine.generation.domain.model.valueobjects.curricular_context import (
    CurricularContext,
)
from kalibra_engine.generation.domain.model.valueobjects.difficulty_level import DifficultyLevel
from kalibra_engine.generation.domain.model.valueobjects.proposed_exercise import (
    ProposedExercise,
)
from kalibra_engine.generation.domain.model.valueobjects.source_document import SourceDocument
from kalibra_engine.generation.domain.model.valueobjects.verification_result import (
    VerificationResult,
)
from kalibra_engine.generation.domain.services.content_normalizer import ContentNormalizer
from kalibra_engine.generation.domain.services.difficulty_targeting_policy import (
    DifficultyTargetingPolicy,
)
from kalibra_engine.generation.infrastructure.providers.deep_seek_flash_adapter import (
    DeepSeekFlashAdapter,
    DeepSeekFlashDraft,
)
from kalibra_engine.generation.infrastructure.providers.mistral_ocr_adapter import (
    MistralDocumentType,
    MistralOcrAdapter,
)
from kalibra_engine.shared.infrastructure.external_provider_error import ExternalProviderError
from kalibra_engine.verification.interfaces.acl.verification_request import VerificationRequest
from kalibra_engine.verification.interfaces.acl.verification_summary import VerificationSummary
from tests.generation.builders import CONTEXT, command, exercise, result


class FakeGenerator(ExternalExerciseGeneratorService):
    def __init__(self) -> None:
        self.targets: list[DifficultyLevel] = []
        self.active = 0
        self.max_active = 0

    async def propose(
        self, context: CurricularContext, target: DifficultyLevel
    ) -> ProposedExercise:
        self.targets.append(target)
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        await asyncio.sleep(0)
        self.active -= 1
        return exercise(f"intento {len(self.targets)}")


class FakeVerifier(ExternalVerificationService):
    def __init__(self, verdicts: list[bool] | None = None, error: Exception | None = None) -> None:
        self.verdicts = verdicts
        self.error = error

    async def verify(
        self, exercise: ProposedExercise, context: CurricularContext, target: DifficultyLevel
    ) -> VerificationResult:
        if self.error is not None:
            raise self.error
        approved = True if self.verdicts is None else self.verdicts.pop(0)
        return result(approved)


def _service(
    generator: FakeGenerator, verifier: FakeVerifier, *, max_attempts: int = 3, concurrency: int = 4
) -> GenerationRunCommandServiceImpl:
    return GenerationRunCommandServiceImpl(
        DifficultyTargetingPolicy(),
        generator,
        verifier,
        max_attempts=max_attempts,
        max_concurrency=concurrency,
    )


class TestGenerationRunCommandService:
    @pytest.mark.anyio
    async def test_discards_rejected_and_retries_until_approved(self) -> None:
        generator = FakeGenerator()

        runs = await _service(generator, FakeVerifier([False, True])).handle(command(mastery=0.8))

        run = runs[0]
        assert run.approved_exercise() is not None
        assert len(run.attempts) == 2
        assert len(run.discarded_attempts()) == 1
        assert generator.targets == [DifficultyLevel.HARD, DifficultyLevel.HARD]

    @pytest.mark.anyio
    async def test_exhausted_run_is_returned_with_every_attempt(self) -> None:
        runs = await _service(FakeGenerator(), FakeVerifier([False, False]), max_attempts=2).handle(
            command()
        )

        assert runs[0].is_exhausted() is True
        assert runs[0].approved_exercise() is None
        assert len(runs[0].attempts) == 2

    @pytest.mark.anyio
    async def test_one_run_per_exercise_with_bounded_concurrency(self) -> None:
        generator = FakeGenerator()

        runs = await _service(generator, FakeVerifier(), concurrency=2).handle(command(quantity=5))

        assert len(runs) == 5
        assert all(run.approved_exercise() is not None for run in runs)
        assert generator.max_active <= 2

    @pytest.mark.anyio
    async def test_provider_failure_propagates_unwrapped(self) -> None:
        verifier = FakeVerifier(error=ExternalProviderError("deepseek", "down"))

        with pytest.raises(ExternalProviderError):
            await _service(FakeGenerator(), verifier).handle(command(quantity=3))


class FakeOcrAdapter(MistralOcrAdapter):
    def __init__(self, pages: list[str] | None = None, error: Exception | None = None) -> None:
        self.pages = pages or []
        self.error = error
        self.calls: list[tuple[str, MistralDocumentType]] = []

    async def extract(self, *, reference: str, document_type: MistralDocumentType) -> list[str]:
        self.calls.append((reference, document_type))
        if self.error is not None:
            raise self.error
        return self.pages


def _status_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "https://api.mistral.ai/v1/ocr")
    return httpx.HTTPStatusError(
        f"HTTP {status_code}", request=request, response=httpx.Response(status_code)
    )


def _extraction(document_format: str = "pdf") -> ExtractCurricularContentCommand:
    return ExtractCurricularContentCommand(
        material_id=uuid4(),
        document=SourceDocument(reference="https://files.test/m.pdf", format=document_format),
    )


class TestCurricularExtraction:
    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ("document_format", "document_type"),
        [("pdf", "document_url"), (".PPTX", "document_url"), ("jpg", "image_url")],
    )
    async def test_routes_format_to_provider_document_type(
        self, document_format: str, document_type: str
    ) -> None:
        adapter = FakeOcrAdapter(pages=["Página 1", "Página 2"])
        service = CurricularExtractionCommandServiceImpl(
            ExternalOcrService(adapter), ContentNormalizer()
        )

        content = await service.handle(_extraction(document_format))

        assert content.normalized_text == "Página 1\n\nPágina 2"
        assert content.page_count == 2
        assert adapter.calls == [("https://files.test/m.pdf", document_type)]

    @pytest.mark.anyio
    async def test_unsupported_format_fails(self) -> None:
        service = CurricularExtractionCommandServiceImpl(
            ExternalOcrService(FakeOcrAdapter()), ContentNormalizer()
        )

        with pytest.raises(ContentExtractionFailedException, match="no está soportado"):
            await service.handle(_extraction("exe"))

    @pytest.mark.anyio
    @pytest.mark.parametrize("status_code", [400, 413, 415, 422])
    async def test_document_rejected_by_provider_is_extraction_failure(
        self, status_code: int
    ) -> None:
        service = CurricularExtractionCommandServiceImpl(
            ExternalOcrService(FakeOcrAdapter(error=_status_error(status_code))),
            ContentNormalizer(),
        )

        with pytest.raises(ContentExtractionFailedException, match="No se pudo extraer"):
            await service.handle(_extraction())

    @pytest.mark.anyio
    async def test_material_without_text_is_extraction_failure(self) -> None:
        service = CurricularExtractionCommandServiceImpl(
            ExternalOcrService(FakeOcrAdapter(pages=["  ", "![img](img.png)"])),
            ContentNormalizer(),
        )

        with pytest.raises(ContentExtractionFailedException, match="no contiene texto"):
            await service.handle(_extraction())

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "error",
        [
            httpx.ConnectError("down"),
            httpx.ReadTimeout("slow"),
            ExternalProviderError("mistral-ocr", "API key is not configured"),
            ExternalProviderError("mistral-ocr", "unexpected OCR response shape"),
            *(_status_error(code) for code in (401, 403, 404, 408, 429, 500, 503)),
        ],
    )
    async def test_provider_failure_is_not_blamed_on_the_material(self, error: Exception) -> None:
        service = CurricularExtractionCommandServiceImpl(
            ExternalOcrService(FakeOcrAdapter(error=error)), ContentNormalizer()
        )

        with pytest.raises(type(error)) as raised:
            await service.handle(_extraction())

        assert raised.value is error


class FakeFlashAdapter(DeepSeekFlashAdapter):
    def __init__(self, draft: DeepSeekFlashDraft) -> None:
        self.draft = draft
        self.kwargs: dict[str, str] = {}

    async def propose(self, **kwargs: str) -> DeepSeekFlashDraft:  # type: ignore[override]
        self.kwargs = kwargs
        return self.draft


class FakeFacade:
    def __init__(self) -> None:
        self.request: VerificationRequest | None = None

    async def verify(self, request: VerificationRequest) -> VerificationSummary:
        self.request = request
        return VerificationSummary(
            approved=False,
            correctness_passed=True,
            difficulty_passed=False,
            rejection_reason="dificultad",
            used_fallback=False,
        )


class TestAcls:
    @pytest.mark.anyio
    async def test_generator_translates_draft_and_orders_options(self) -> None:
        draft = DeepSeekFlashDraft.model_validate(
            {
                "statement": "¿2+2?",
                "options": [
                    {"key": "B", "text": "3"},
                    {"key": "A", "text": "4"},
                    {"key": "D", "text": "6"},
                    {"key": "C", "text": "5"},
                ],
                "correct_option_key": "A",
                "explanation": "suma",
                "difficulty": "MEDIUM",
            }
        )
        adapter = FakeFlashAdapter(draft)

        proposed = await ExternalExerciseGeneratorService(adapter).propose(
            CONTEXT, DifficultyLevel.MEDIUM
        )

        assert [option.key for option in proposed.options] == ["A", "B", "C", "D"]
        assert proposed.difficulty is DifficultyLevel.MEDIUM
        assert adapter.kwargs == {
            "subtopic_name": "Derivadas",
            "curricular_content": "Regla de la potencia.",
            "target_difficulty": "MEDIUM",
        }

    @pytest.mark.anyio
    async def test_verification_acl_translates_contract(self) -> None:
        facade = FakeFacade()

        verdict = await ExternalVerificationService(facade).verify(
            exercise(), CONTEXT, DifficultyLevel.HARD
        )

        assert facade.request == VerificationRequest(
            statement="¿Derivada de x^2?",
            options=("2x", "x", "x^2", "2"),
            correct_option_key="A",
            declared_difficulty="EASY",
            target_difficulty="HARD",
            curricular_context="Regla de la potencia.",
        )
        assert verdict.approved is False
        assert verdict.difficulty_passed is False
        assert verdict.rejection_reason == "dificultad"
