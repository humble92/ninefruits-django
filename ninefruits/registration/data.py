"""Values passed between the registration rules, the engine and the actions (original
``App\\Domain\\Registration\\Data``)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from ninefruits.registration.enums import AttemptAction, AttemptOutcome, EnrollmentSource, RuleCode, RuleSeverity

if TYPE_CHECKING:
    from ninefruits.offering.models import Section
    from ninefruits.person.models import StudentRecord
    from ninefruits.registration.models import Enrollment, WaitlistEntry


@dataclass(frozen=True)
class EnrollOptions:
    """How an enroll attempt runs. Staff may waive rules that allow overrides, with a reason."""

    waitlist_if_full: bool = False
    waive: tuple[RuleCode, ...] = ()
    reason: str | None = None
    source: EnrollmentSource | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "waive", tuple(RuleCode(code) for code in self.waive))


@dataclass
class RegistrationContext:
    """What a registration rule looks at: who, which section, what action, when, and the
    student's other enrollments in the term."""

    record: StudentRecord
    section: Section
    action: AttemptAction
    at: datetime
    actor: Any = None
    by_staff: bool = False
    #: Rules staff chose to waive for this action (with a reason).
    waived: tuple[RuleCode, ...] = ()
    _term_enrollments: list[Enrollment] | None = field(default=None, repr=False)

    def term_enrollments(self) -> list[Enrollment]:
        """Active enrollments of the student in the section's term, other than this section."""
        if self._term_enrollments is None:
            from ninefruits.registration.models import Enrollment

            self._term_enrollments = list(
                Enrollment.objects.active()
                .filter(student_record_id=self.record.pk, term_id=self.section.term_id)
                .exclude(section_id=self.section.pk)
                .select_related("section__course")
                .prefetch_related("section__meetings")
            )
        return self._term_enrollments


@dataclass(frozen=True)
class RuleCheck:
    """The outcome of one rule before configuration (severity, overrides) is applied.
    ``details`` are facts for the explanation (limits, conflicts ...)."""

    passed: bool
    message: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, message: str | None = None, details: dict[str, Any] | None = None) -> RuleCheck:
        return cls(True, message, details or {})

    @classmethod
    def fail(cls, message: str, details: dict[str, Any] | None = None) -> RuleCheck:
        return cls(False, message, details or {})


@dataclass(frozen=True)
class RuleResult:
    """One rule's result as configured: a failed rule blocks unless it only warns or was
    overridden."""

    code: RuleCode
    passed: bool
    severity: RuleSeverity
    overridden: bool
    message: str | None
    details: dict[str, Any] = field(default_factory=dict)

    def blocks(self) -> bool:
        return not self.passed and not self.overridden and self.severity == RuleSeverity.BLOCK

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": str(self.code.value),
            "passed": self.passed,
            "severity": str(RuleSeverity(self.severity).value),
            "overridden": self.overridden,
            "message": None if self.message is None else str(self.message),
        }


@dataclass(frozen=True)
class RuleEvaluation:
    """All rule results of one attempt. The engine never stops at the first failure, so the
    student and staff see every reason at once."""

    results: tuple[RuleResult, ...]

    def is_blocked(self) -> bool:
        return any(result.blocks() for result in self.results)

    def blocking(self) -> list[RuleResult]:
        return [result for result in self.results if result.blocks()]

    def blocking_messages(self) -> list[str]:
        return [str(result.message) for result in self.results if result.blocks() and result.message]

    def warnings(self) -> list[str]:
        """Failed rules that only warn or were overridden."""
        return [
            str(result.message)
            for result in self.results
            if not result.passed and not result.blocks() and result.message
        ]

    def detail(self, key: str) -> Any:
        for result in self.results:
            if key in result.details:
                return result.details[key]
        return None

    def with_result(
        self, code: RuleCode, message: str, *, passed: bool = False, severity: RuleSeverity = RuleSeverity.BLOCK
    ) -> RuleEvaluation:
        return RuleEvaluation((*self.results, RuleResult(code, passed, severity, False, message)))

    def to_list(self) -> list[dict[str, Any]]:
        return [result.to_dict() for result in self.results]


@dataclass(frozen=True)
class RegistrationOutcome:
    """Result of an enroll attempt: enrolled, on the waitlist, or refused (with every reason)."""

    outcome: AttemptOutcome
    evaluation: RuleEvaluation
    enrollment: Enrollment | None = None
    waitlist_entry: WaitlistEntry | None = None

    def succeeded(self) -> bool:
        return self.outcome == AttemptOutcome.SUCCEEDED

    def refused_for_seat(self) -> bool:
        """Refused only because no seat was free for this student."""
        if self.outcome != AttemptOutcome.REFUSED:
            return False
        blocking = self.evaluation.blocking()
        return len(blocking) == 1 and blocking[0].code == RuleCode.CAPACITY

    def messages(self) -> list[str]:
        if self.outcome == AttemptOutcome.REFUSED:
            return self.evaluation.blocking_messages()
        return self.evaluation.warnings()
