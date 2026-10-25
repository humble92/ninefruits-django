"""Demo registrations (original ``Database\\Seeders\\Demo\\DemoRegistrationSeeder``).

Rule sets for the current and next term (the next copied from the current), one credit limit
per term type (18 regular, 6 seasonal), registrations of enrolled students in the current term
(up to five sections each, tried from up to ten sections that admit them), one small next-term
section with two students registered and two waiting, and two financial holds.

The original registered every student through ``EnrollStudent`` (staff, window waived). Here the
current-term registrations are decided in memory with the same rules (section eligibility, the
same course twice, time conflicts, credit limit, prerequisites, retakes, reserved and general
seats) and written with bulk inserts: enrollments, one attempt log row per try, and the seat
counters. ``--size=large`` therefore takes seconds instead of the original's many minutes. The
small waitlist section, the holds and the rule sets still go through the actions."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from django.db.models import Q
from django.utils import timezone

from ninefruits.core.targeting import TargetCriteria
from ninefruits.curriculum.enums import RequisiteKind
from ninefruits.offering.enums import SectionStatus
from ninefruits.offering.models import Section, SectionSeatGroup
from ninefruits.person.enums import StudentStatus
from ninefruits.person.models import StudentRecord, StudentRecordProgram
from ninefruits.registration.actions import EnrollStudent, ManageHolds, PrepareRuleSet
from ninefruits.registration.actions.enroll_student import full_message
from ninefruits.registration.data import EnrollOptions
from ninefruits.registration.enums import (
    AttemptAction,
    AttemptOutcome,
    EnrollmentSource,
    EnrollmentStatus,
    HoldType,
    RuleCode,
    RuleSeverity,
)
from ninefruits.registration.models import CreditLimitPolicy, Enrollment, RegistrationAttempt, RegistrationRuleSet
from ninefruits.registration.rules.credit_limit import limit_message
from ninefruits.registration.rules.duplicate_course import duplicate_message
from ninefruits.registration.rules.repeat_course import retake_message
from ninefruits.registration.rules.requisites import missing_message
from ninefruits.registration.rules.time_conflict import conflict_message, overlap_minutes
from ninefruits.registration.rules.window import window_failed
from ninefruits.registration.services.course_history import CourseHistory
from ninefruits.setup import conf
from ninefruits.setup.seeders.base import Seeder
from ninefruits.term.enums import TermStatus, TermWindowType
from ninefruits.term.models import Term, TermType, TermWindow

from .options import current_options

REASON = "Demo data"
BATCH = 2000
#: Sections registered per student and sections tried (original: 5 of up to 10).
PER_STUDENT = 5
TRIED = 10


@dataclass
class _Subject:
    """A student record with its targeting facts loaded once (``TargetSubject``)."""

    record: StudentRecord
    program_ids: list[int]
    org_unit_ids: list[int]

    def target_program_ids(self) -> list[int]:
        return self.program_ids

    def target_org_unit_ids(self) -> list[int]:
        return self.org_unit_ids

    def target_admission_year(self) -> int | None:
        return self.record.admission_date.year

    def target_year_level(self) -> int | None:
        return self.record.year_level

    def target_student_status(self) -> str | None:
        return str(self.record.status)

    def target_academic_standing(self) -> str | None:
        return self.record.academic_standing

    def target_tags(self) -> list[str]:
        return [str(tag) for tag in (self.record.tags or [])]


@dataclass
class _Plan:
    """What a student has registered so far in the term."""

    course_ids: set[int] = field(default_factory=set)
    meetings: list[tuple[str, Any]] = field(default_factory=list)
    credits: Decimal = Decimal(0)
    count: int = 0


class DemoRegistrationSeeder(Seeder):
    def run(self) -> None:
        from ninefruits.security.models import User

        registrar = User.objects.filter(email=f"registrar@{conf.DEMO_EMAIL_DOMAIN}").first()
        today = timezone.localdate()
        current = (
            Term.objects.filter(status=TermStatus.PUBLISHED, start_date__lte=today).order_by("-start_date").first()
        )
        upcoming = Term.objects.filter(status=TermStatus.PUBLISHED, start_date__gt=today).order_by("start_date").first()
        if registrar is None or current is None or Enrollment.objects.filter(term=current).exists():
            return

        prepare = PrepareRuleSet()
        current_set = RegistrationRuleSet.objects.filter(term=current).first() or prepare.handle(
            current, None, registrar
        )
        if upcoming is not None and not RegistrationRuleSet.objects.filter(term=upcoming).exists():
            prepare.handle(upcoming, current_set, registrar)

        self.credit_limits()
        options = current_options()
        records = list(
            StudentRecord.objects.filter(status=StudentStatus.ENROLLED)
            .select_related("person")
            .order_by("student_number")
        )
        options.rng.shuffle(records)
        students = records[: options.scale(60)]
        self.registrations(current, students, registrar)
        if upcoming is not None:
            self.waitlist(upcoming, registrar)
        for record in students[:2]:
            ManageHolds().place(record, HoldType.FINANCIAL, "Unpaid tuition (demo)", registrar)

    # -- credit limits ----------------------------------------------------------------------------
    def credit_limits(self) -> None:
        if CreditLimitPolicy.objects.exists():
            return
        rows = []
        for term_type in TermType.objects.order_by("sort_order", "id"):
            regular = bool(term_type.is_regular)
            rows.append(
                CreditLimitPolicy(
                    name=(
                        {"en": "Regular term", "ko": "정규학기", "zh-hans": "正常学期"}
                        if regular
                        else {"en": "Seasonal term", "ko": "계절학기", "zh-hans": "短学期"}
                    ),
                    term_type=term_type,
                    eligibility=TargetCriteria.everyone(),
                    max_credits=18 if regular else 6,
                    priority=0,
                )
            )
        CreditLimitPolicy.objects.bulk_create(rows)

    # -- current term ------------------------------------------------------------------------------
    def registrations(self, term: Term, students: list[StudentRecord], registrar: Any) -> None:
        rng = current_options().rng
        now = timezone.now().replace(microsecond=0)
        sections = list(
            Section.objects.filter(term=term, status=SectionStatus.PUBLISHED)
            .select_related("course", "version")
            .prefetch_related("meetings", "seat_groups", "version__requisites__required_course")
            .order_by("pk")
        )
        if not sections or not students:
            return
        subjects = self._subjects(students)
        policies = list(
            CreditLimitPolicy.objects.filter(is_active=True)
            .filter(Q(term_type_id__isnull=True) | Q(term_type_id=term.term_type_id))
            .order_by("-priority", "id")
        )
        window_open = self._window_open(term, now)
        history = self.history = CourseHistory()
        accepted: dict[int, list[int]] = {}

        def accepted_ids(course_id: int) -> list[int]:
            if course_id not in accepted:
                accepted[course_id] = history.accepted_course_ids(course_id, term.start_date)
            return accepted[course_id]

        passed, completed = self._history(students)
        seats = {section.pk: section.enrolled_count for section in sections}
        groups: dict[int, list[SectionSeatGroup]] = {s.pk: list(s.seat_groups.all()) for s in sections}
        enrollments: list[Enrollment] = []
        attempts: list[RegistrationAttempt] = []

        for record in students:
            subject = subjects[record.pk]
            policy = next((p for p in policies if p.eligibility.matches(subject)), None)
            candidates = [section for section in sections if section.admits(subject)]
            rng.shuffle(candidates)
            plan = _Plan()
            for section in candidates[:TRIED]:
                results, retake_of = self._evaluate(
                    record, section, plan, policy, window_open, passed, completed, accepted_ids
                )
                blocked = any(not r["passed"] and not r["overridden"] for r in results)
                seat_group: SectionSeatGroup | None = None
                if not blocked:
                    seat = self._seat(section, seats, groups[section.pk], subject, now)
                    if seat is None:
                        blocked = True
                        results.append(_result(RuleCode.CAPACITY, False, _message("full", lambda: full_message(False))))
                    elif isinstance(seat, SectionSeatGroup):
                        seat_group = seat
                attempts.append(
                    RegistrationAttempt(
                        student_record=record,
                        term=term,
                        section=section,
                        action=AttemptAction.ENROLL,
                        outcome=AttemptOutcome.REFUSED if blocked else AttemptOutcome.SUCCEEDED,
                        results=results,
                        actor=registrar,
                        attempted_at=now,
                    )
                )
                if blocked:
                    continue
                seats[section.pk] += 1
                if seat_group is not None:
                    seat_group.enrolled_count += 1
                version = section.version
                enrollments.append(
                    Enrollment(
                        student_record=record,
                        section=section,
                        term=term,
                        course_id=section.course_id,
                        version=version,
                        credits=version.credits,
                        category_id=version.category_id,
                        counts_toward_credit_limit=version.counts_toward_credit_limit,
                        seat_group=seat_group,
                        is_retake=retake_of is not None,
                        repeats_enrollment_id=retake_of,
                        source=EnrollmentSource.STAFF,
                        enrolled_at=now,
                        changed_by=registrar,
                    )
                )
                plan.course_ids.add(section.course_id)
                plan.meetings.extend((section.label(), meeting) for meeting in section.meetings.all())
                if version.counts_toward_credit_limit:
                    plan.credits += Decimal(version.credits)
                plan.count += 1
                if plan.count >= PER_STUDENT:
                    break

        Enrollment.objects.bulk_create(enrollments, batch_size=BATCH)
        RegistrationAttempt.objects.bulk_create(attempts, batch_size=BATCH)
        # Counters only (no updated_at), like SeatAllocator.take.
        for section in sections:
            section.enrolled_count = seats[section.pk]
        Section.objects.bulk_update(sections, ["enrolled_count"], batch_size=BATCH)
        SectionSeatGroup.objects.bulk_update(
            [group for section_groups in groups.values() for group in section_groups],
            ["enrolled_count"],
            batch_size=BATCH,
        )

    def _evaluate(
        self,
        record: StudentRecord,
        section: Section,
        plan: _Plan,
        policy: CreditLimitPolicy | None,
        window_open: bool,
        passed: dict[int, dict[int, list[str | None]]],
        completed: dict[int, dict[int, int]],
        accepted_ids: Any,
    ) -> tuple[list[dict[str, Any]], int | None]:
        """The rule results of the catalog defaults, as ``RegistrationRuleEngine`` records them
        for a staff registration (window waived)."""
        version = section.version
        results = [
            _result(
                RuleCode.WINDOW,
                window_open,
                None if window_open else _message("window", lambda: window_failed(AttemptAction.ENROLL)),
                overridden=not window_open,
            ),
            _result(RuleCode.SECTION_OPEN, True),
            _result(RuleCode.HOLD, True),
            _result(RuleCode.STUDENT_STATUS, True),
            _result(RuleCode.ELIGIBILITY, True),
        ]
        duplicate = section.course_id in plan.course_ids
        results.append(
            _result(
                RuleCode.DUPLICATE_COURSE,
                not duplicate,
                _message(("duplicate", section.pk), lambda: duplicate_message(section.label())) if duplicate else None,
            )
        )
        conflict = next(
            (
                label
                for label, other in plan.meetings
                for meeting in section.meetings.all()
                if meeting.is_active and overlap_minutes(meeting, other) > 0
            ),
            None,
        )
        results.append(
            _result(
                RuleCode.TIME_CONFLICT,
                conflict is None,
                None if conflict is None else _message(("conflict", conflict), lambda: conflict_message(conflict)),
            )
        )
        if policy is not None and version.counts_toward_credit_limit:
            total = plan.credits + Decimal(version.credits)
            within = total <= policy.max_credits
            message = None if within else limit_message(total, policy.max_credits)
            results.append(_result(RuleCode.CREDIT_LIMIT, within, message))
        else:
            results.append(_result(RuleCode.CREDIT_LIMIT, True))

        person_passed = passed.get(record.person_id, {})
        groups: dict[str, list[Any]] = defaultdict(list)
        for requisite in version.requisites.all():
            groups[f"{requisite.kind}-{requisite.group_number}"].append(requisite)
        missing = []
        for group in groups.values():
            met = False
            for requisite in group:
                ids = accepted_ids(requisite.required_course_id)
                concurrent = requisite.kind == RequisiteKind.COREQUISITE or requisite.allows_concurrent
                grades = [grade for course_id in ids for grade in person_passed.get(course_id, [])]
                if any(
                    requisite.minimum_grade is None or self.history.meets_minimum(grade, requisite.minimum_grade)
                    for grade in grades
                ) or (concurrent and plan.course_ids.intersection(ids)):
                    met = True
                    break
            if not met:
                missing.append(" / ".join(requisite.required_course.code for requisite in group))
        results.append(
            _result(
                RuleCode.REQUISITES,
                not missing,
                _message(
                    ("requisites", *missing),
                    lambda: missing_message(missing),
                )
                if missing
                else None,
            )
        )

        retake_of = None
        if not version.is_repeatable:
            earlier = [completed.get(record.pk, {}).get(course_id) for course_id in accepted_ids(section.course_id)]
            earlier_ids = [enrollment_id for enrollment_id in earlier if enrollment_id is not None]
            retake_of = max(earlier_ids) if earlier_ids else None
        results.append(_result(RuleCode.REPEAT_COURSE, True, _message("retake", retake_message) if retake_of else None))
        return results, retake_of

    @staticmethod
    def _seat(
        section: Section, seats: dict[int, int], groups: list[SectionSeatGroup], subject: _Subject, at: datetime
    ) -> SectionSeatGroup | str | None:
        """``SeatAllocator.find`` on the in-memory counters."""
        reserved = [group for group in groups if group.is_reserved_at(at)]
        group = next((g for g in reserved if g.enrolled_count < g.capacity and g.eligibility.matches(subject)), None)
        if group is not None:
            return group
        unused = sum(max(0, g.capacity - g.enrolled_count) for g in reserved)
        return "general" if section.capacity - seats[section.pk] - unused > 0 else None

    @staticmethod
    def _subjects(students: list[StudentRecord]) -> dict[int, _Subject]:
        from ninefruits.organization.models import OrgUnit

        ids = [record.pk for record in students]
        extra: dict[int, list[tuple[int, int]]] = defaultdict(list)
        for row in StudentRecordProgram.objects.filter(student_record_id__in=ids, end_date__isnull=True).values_list(
            "student_record_id", "program_id", "program__org_unit_id"
        ):
            extra[row[0]].append((row[1], row[2]))
        ancestors: dict[int, list[int]] = {unit.pk: unit.ancestor_ids() for unit in OrgUnit.objects.all()}

        subjects = {}
        for record in students:
            units = list(dict.fromkeys([record.org_unit_id, *(unit for _program, unit in extra[record.pk])]))
            org_unit_ids: list[int] = []
            for unit in units:
                for ancestor in ancestors.get(unit, [unit]):
                    if ancestor not in org_unit_ids:
                        org_unit_ids.append(ancestor)
            subjects[record.pk] = _Subject(
                record, [record.program_id, *(program for program, _unit in extra[record.pk])], org_unit_ids
            )
        return subjects

    @staticmethod
    def _history(
        students: list[StudentRecord],
    ) -> tuple[dict[int, dict[int, list[str | None]]], dict[int, dict[int, int]]]:
        """Passed courses per person (grades) and the latest completed enrollment per record and
        course."""
        passed: dict[int, dict[int, list[str | None]]] = defaultdict(lambda: defaultdict(list))
        completed: dict[int, dict[int, int]] = defaultdict(dict)
        person_ids = {record.person_id for record in students}
        rows = (
            Enrollment.objects.filter(student_record__person_id__in=person_ids, status=EnrollmentStatus.COMPLETED)
            .order_by("enrolled_at", "pk")
            .values_list("pk", "student_record_id", "student_record__person_id", "course_id", "grade_code", "is_passed")
        )
        for pk, record_id, person_id, course_id, grade, is_passed in rows:
            if is_passed:
                passed[person_id][course_id].append(grade)
            completed[record_id][course_id] = pk
        return passed, completed

    @staticmethod
    def _window_open(term: Term, at: datetime) -> bool:
        return TermWindow.objects.filter(
            Q(term=term, window_type=TermWindowType.REGISTRATION) | Q(term=term, window_type=TermWindowType.ADD_DROP),
            opens_at__lte=at,
            closes_at__gt=at,
        ).exists()

    # -- next term -------------------------------------------------------------------------------
    def waitlist(self, term: Term, registrar: Any) -> None:
        """One small next-term section: two seats taken, two students waiting."""
        section = (
            Section.objects.filter(term=term, status=SectionStatus.PUBLISHED, seat_groups__isnull=True)
            .select_related("course", "version", "session")
            .order_by("pk")
            .first()
        )
        if section is None:
            return
        section.capacity = 2
        section.waitlist_capacity = 5
        section.save(update_fields=["capacity", "waitlist_capacity", "updated_at"])
        students: list[StudentRecord] = []
        for record in StudentRecord.objects.filter(status=StudentStatus.ENROLLED).order_by("student_number").iterator():
            if section.admits(record):
                students.append(record)
            if len(students) == 4:
                break
        enroll = EnrollStudent()
        for record in students:
            enroll.handle(
                record,
                section,
                registrar,
                EnrollOptions(waitlist_if_full=True, waive=(RuleCode.WINDOW,), reason=REASON),
            )


_messages: dict[Any, str] = {}


def _message(key: Any, build: Any) -> str:
    """Rule messages repeat for every student: translate each once per run (language included)."""
    from django.utils.translation import get_language

    full_key = (get_language(), key)
    if full_key not in _messages:
        _messages[full_key] = str(build())
    return _messages[full_key]


def _result(code: RuleCode, passed: bool, message: str | None = None, *, overridden: bool = False) -> dict[str, Any]:
    return {
        "code": code.value,
        "passed": passed,
        "severity": RuleSeverity.BLOCK.value,
        "overridden": overridden,
        "message": message,
    }
