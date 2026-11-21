import pytest

from kalibra_engine.verification.domain.model.aggregates.exercise_verification import (
    ExerciseVerification,
)
from kalibra_engine.verification.domain.model.commands.verify_exercise_command import (
    VerifyExerciseCommand,
)
from kalibra_engine.verification.domain.model.entities.verification_check import (
    VerificationCheck,
)
from kalibra_engine.verification.domain.model.valueobjects.check_source import CheckSource
from kalibra_engine.verification.domain.model.valueobjects.difficulty_level import (
    DifficultyLevel,
)
from kalibra_engine.verification.domain.model.valueobjects.rejection_reason import (
    RejectionReason,
)
from kalibra_engine.verification.domain.model.valueobjects.verification_criterion import (
    VerificationCriterion,
)
from kalibra_engine.verification.domain.model.valueobjects.verification_verdict import (
    VerificationVerdict,
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
from tests.verification.builders import candidate

CORRECTNESS = VerificationCriterion.CORRECTNESS
DIFFICULTY = VerificationCriterion.DIFFICULTY


def _check(
    criterion: VerificationCriterion, passed: bool, source: CheckSource = CheckSource.RULES
) -> VerificationCheck:
    return VerificationCheck(criterion=criterion, passed=passed, detail="d", decided_by=source)


def _verification() -> ExerciseVerification:
    return ExerciseVerification.evaluate(
        VerifyExerciseCommand(candidate=candidate(), target_difficulty=DifficultyLevel.EASY)
    )


class TestCorrectnessCheckPolicy:
    def test_well_formed_exercise_passes(self) -> None:
        check = CorrectnessCheckPolicy().check(candidate())

        assert check.passed is True
        assert check.criterion is CORRECTNESS
        assert check.decided_by is CheckSource.RULES

    @pytest.mark.parametrize(
        ("overrides", "fragment"),
        [
            ({"statement": "   "}, "enunciado está vacío"),
            ({"options": ("a", "b", "c")}, "4 alternativas y tiene 3"),
            ({"options": ("a", " ", "c", "d")}, "alternativas vacías"),
            ({"options": ("2x", "2X ", "x", "1")}, "alternativas repetidas"),
            ({"correct_option_key": "E"}, "no corresponde a ninguna"),
        ],
    )
    def test_structural_rule_violations_fail(
        self, overrides: dict[str, object], fragment: str
    ) -> None:
        check = CorrectnessCheckPolicy().check(candidate(**overrides))

        assert check.passed is False
        assert fragment in check.detail


class TestDifficultyCheckPolicy:
    def test_matching_difficulty_passes(self) -> None:
        assert DifficultyCheckPolicy().check(candidate(), DifficultyLevel.EASY).passed is True

    def test_mismatching_difficulty_fails(self) -> None:
        check = DifficultyCheckPolicy().check(candidate(), DifficultyLevel.HARD)

        assert check.passed is False
        assert check.criterion is DIFFICULTY


class TestFallbackEscalationPolicy:
    @pytest.mark.parametrize(
        ("check", "expected"),
        [
            (_check(CORRECTNESS, True), True),
            (_check(CORRECTNESS, False), False),
            (_check(DIFFICULTY, True), False),
            (_check(CORRECTNESS, True, CheckSource.FALLBACK_PROVIDER), False),
        ],
    )
    def test_only_rule_approved_correctness_escalates(
        self, check: VerificationCheck, expected: bool
    ) -> None:
        assert FallbackEscalationPolicy().requires_fallback(check) is expected


class TestExerciseVerification:
    def test_starts_open(self) -> None:
        verification = _verification()

        assert verification.verdict is None
        assert verification.checks == ()
        assert verification.is_approved() is False
        assert verification.target_difficulty is DifficultyLevel.EASY
        assert verification.candidate == candidate()

    def test_approves_when_latest_check_of_each_criterion_passed(self) -> None:
        verification = _verification()
        verification.record(_check(CORRECTNESS, True))
        verification.record(_check(DIFFICULTY, True))

        verification.approve()

        assert verification.verdict is VerificationVerdict.APPROVED
        assert verification.is_approved() is True
        assert verification.rejection_reason is None

    def test_cannot_approve_with_a_missing_criterion(self) -> None:
        verification = _verification()
        verification.record(_check(CORRECTNESS, True))

        with pytest.raises(ValueError, match="every criterion"):
            verification.approve()

    def test_latest_fallback_check_overrides_rules(self) -> None:
        verification = _verification()
        verification.record(_check(CORRECTNESS, True))
        verification.record(_check(DIFFICULTY, True))
        verification.record(_check(CORRECTNESS, False, CheckSource.FALLBACK_PROVIDER))

        assert verification.used_fallback is True
        assert verification.criterion_passed(CORRECTNESS) is False
        with pytest.raises(ValueError):
            verification.approve()

    def test_discard_keeps_reason(self) -> None:
        verification = _verification()
        reason = RejectionReason(criterion=DIFFICULTY, description="muy difícil")

        verification.discard(reason)

        assert verification.verdict is VerificationVerdict.DISCARDED
        assert verification.rejection_reason == reason

    def test_decided_verification_is_closed(self) -> None:
        verification = _verification()
        verification.discard(RejectionReason(criterion=DIFFICULTY, description="x"))

        with pytest.raises(ValueError, match="already has a verdict"):
            verification.record(_check(CORRECTNESS, True))
