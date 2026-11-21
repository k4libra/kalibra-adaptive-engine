import httpx
import pytest

from kalibra_engine.shared.infrastructure.settings import Settings
from kalibra_engine.verification.application.acl.verification_context_facade_impl import (
    VerificationContextFacadeImpl,
)
from kalibra_engine.verification.application.internal.commandservices.exercise_verification_command_service_impl import (  # noqa: E501
    ExerciseVerificationCommandServiceImpl,
)
from kalibra_engine.verification.application.internal.outboundservices.acl.external_verification_fallback_service import (  # noqa: E501
    ExternalVerificationFallbackService,
)
from kalibra_engine.verification.domain.model.commands.verify_exercise_command import (
    VerifyExerciseCommand,
)
from kalibra_engine.verification.domain.model.entities.verification_check import (
    VerificationCheck,
)
from kalibra_engine.verification.domain.model.valueobjects.candidate_exercise import (
    CandidateExercise,
)
from kalibra_engine.verification.domain.model.valueobjects.check_source import CheckSource
from kalibra_engine.verification.domain.model.valueobjects.difficulty_level import (
    DifficultyLevel,
)
from kalibra_engine.verification.domain.model.valueobjects.verification_criterion import (
    VerificationCriterion,
)
from kalibra_engine.verification.domain.services.correctness_check_policy import (
    CorrectnessCheckPolicy,
)
from kalibra_engine.verification.domain.services.difficulty_check_policy import (
    DifficultyCheckPolicy,
)
from kalibra_engine.verification.domain.services.fallback_escalation_policy import (
    FallbackEscalationPolicy,
)
from kalibra_engine.verification.infrastructure.providers.deep_seek_pro_adapter import (
    DeepSeekProAdapter,
    DeepSeekProReview,
)
from kalibra_engine.verification.interfaces.acl.verification_request import VerificationRequest
from tests.verification.builders import candidate


class FakeFallbackService(ExternalVerificationFallbackService):
    def __init__(self, check: VerificationCheck) -> None:
        self.check = check
        self.calls = 0

    async def review(
        self, candidate: CandidateExercise, target: DifficultyLevel
    ) -> VerificationCheck:
        self.calls += 1
        return self.check


class FakeAdapter(DeepSeekProAdapter):
    def __init__(self, review: DeepSeekProReview) -> None:
        self._review = review

    async def review(self, **_: object) -> DeepSeekProReview:  # type: ignore[override]
        return self._review


def _review(key: str, difficulty_matches: bool) -> DeepSeekProReview:
    return DeepSeekProReview.model_validate(
        {"solved_option_key": key, "difficulty_matches": difficulty_matches, "justification": "x"}
    )


def _fallback_check(passed: bool, criterion: VerificationCriterion) -> VerificationCheck:
    return VerificationCheck(
        criterion=criterion,
        passed=passed,
        detail="respaldo",
        decided_by=CheckSource.FALLBACK_PROVIDER,
    )


def _service(
    fallback: ExternalVerificationFallbackService,
) -> ExerciseVerificationCommandServiceImpl:
    return ExerciseVerificationCommandServiceImpl(
        CorrectnessCheckPolicy(), DifficultyCheckPolicy(), FallbackEscalationPolicy(), fallback
    )


def _command(
    target: DifficultyLevel = DifficultyLevel.EASY, **overrides: object
) -> VerifyExerciseCommand:
    return VerifyExerciseCommand(candidate=candidate(**overrides), target_difficulty=target)


class TestExerciseVerificationCommandService:
    @pytest.mark.anyio
    async def test_approves_after_fallback_confirms(self) -> None:
        fallback = FakeFallbackService(_fallback_check(True, VerificationCriterion.CORRECTNESS))

        verification = await _service(fallback).handle(_command())

        assert verification.is_approved() is True
        assert verification.used_fallback is True
        assert fallback.calls == 1

    @pytest.mark.anyio
    async def test_rule_failure_discards_without_calling_fallback(self) -> None:
        fallback = FakeFallbackService(_fallback_check(True, VerificationCriterion.CORRECTNESS))

        verification = await _service(fallback).handle(_command(correct_option_key="Z"))

        assert verification.is_approved() is False
        assert verification.rejection_reason is not None
        assert verification.rejection_reason.criterion is VerificationCriterion.CORRECTNESS
        assert fallback.calls == 0

    @pytest.mark.anyio
    async def test_difficulty_rule_failure_discards(self) -> None:
        fallback = FakeFallbackService(_fallback_check(True, VerificationCriterion.CORRECTNESS))

        verification = await _service(fallback).handle(_command(DifficultyLevel.HARD))

        assert verification.rejection_reason is not None
        assert verification.rejection_reason.criterion is VerificationCriterion.DIFFICULTY
        assert fallback.calls == 0

    @pytest.mark.anyio
    async def test_fallback_rejection_discards(self) -> None:
        fallback = FakeFallbackService(_fallback_check(False, VerificationCriterion.DIFFICULTY))

        verification = await _service(fallback).handle(_command())

        assert verification.is_approved() is False
        assert verification.rejection_reason is not None
        assert verification.rejection_reason.description == "respaldo"


class TestExternalVerificationFallbackService:
    @pytest.mark.anyio
    async def test_matching_answer_and_difficulty_passes(self) -> None:
        review = _review("A", True)

        check = await ExternalVerificationFallbackService(FakeAdapter(review)).review(
            candidate(), DifficultyLevel.EASY
        )

        assert check.passed is True
        assert check.decided_by is CheckSource.FALLBACK_PROVIDER

    @pytest.mark.anyio
    async def test_different_answer_fails_correctness(self) -> None:
        review = _review("B", True)

        check = await ExternalVerificationFallbackService(FakeAdapter(review)).review(
            candidate(), DifficultyLevel.EASY
        )

        assert check.passed is False
        assert check.criterion is VerificationCriterion.CORRECTNESS
        assert "«B»" in check.detail

    @pytest.mark.anyio
    async def test_wrong_difficulty_fails_difficulty(self) -> None:
        review = _review("A", False)

        check = await ExternalVerificationFallbackService(FakeAdapter(review)).review(
            candidate(), DifficultyLevel.EASY
        )

        assert check.passed is False
        assert check.criterion is VerificationCriterion.DIFFICULTY


class TestVerificationContextFacadeImpl:
    def _request(self, **overrides: object) -> VerificationRequest:
        values: dict[str, object] = {
            "statement": "¿Cuánto es la derivada de x^2?",
            "options": ("2x", "x", "x^2", "2"),
            "correct_option_key": "A",
            "declared_difficulty": "EASY",
            "target_difficulty": "EASY",
            "curricular_context": "Derivadas.",
        }
        values.update(overrides)
        return VerificationRequest(**values)  # type: ignore[arg-type]

    @pytest.mark.anyio
    async def test_approved_summary(self) -> None:
        fallback = FakeFallbackService(_fallback_check(True, VerificationCriterion.CORRECTNESS))
        facade = VerificationContextFacadeImpl(_service(fallback))

        summary = await facade.verify(self._request())

        assert summary.approved is True
        assert summary.correctness_passed is True
        assert summary.difficulty_passed is True
        assert summary.rejection_reason is None
        assert summary.used_fallback is True

    @pytest.mark.anyio
    async def test_discarded_summary_carries_reason(self) -> None:
        fallback = FakeFallbackService(_fallback_check(True, VerificationCriterion.CORRECTNESS))
        facade = VerificationContextFacadeImpl(_service(fallback))

        summary = await facade.verify(self._request(target_difficulty="HARD"))

        assert summary.approved is False
        assert summary.correctness_passed is True
        assert summary.difficulty_passed is False
        assert summary.rejection_reason is not None
        assert summary.used_fallback is False


class TestDeepSeekProAdapter:
    @pytest.mark.anyio
    async def test_sends_json_mode_request_without_keyed_answer(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            content = (
                '{"solved_option_key": "A", "difficulty_matches": true, "justification": "ok"}'
            )
            return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

        settings = Settings(deepseek_api_key="secret")  # type: ignore[arg-type]
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            review = await DeepSeekProAdapter(client, settings).review(
                statement="¿2+2?",
                options=("4", "3", "5", "6"),
                target_difficulty="EASY",
                curricular_context="Aritmética.",
            )

        assert review.solved_option_key == "A"
        request = captured[0]
        assert str(request.url) == "https://api.deepseek.com/chat/completions"
        assert request.headers["authorization"] == "Bearer secret"
        body = request.read().decode()
        assert '"model":"deepseek-v4-pro"' in body
        assert '"response_format":{"type":"json_object"}' in body
        assert "A) 4" in body
