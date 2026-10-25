"""Demo examinations (original ``DemoAssessmentSeeder``): two past English sessions with published
results, a computer exam with pass/fail results, an upcoming English session open for
registration, TOPIK results recorded from certificates, and the English exam as a graduation
requirement in every primary curriculum.

The original entered each past result through the action. Past registrations, results and area
scores are decided in memory here (the same rule: total at or above the pass score, every area at
or above its minimum) and written with bulk inserts; the upcoming session's registrations, the
external results and the publications go through the actions, like staff would."""

from __future__ import annotations

import calendar
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from django.utils import timezone

from ninefruits.assessment.actions import RecordAssessmentResult, RegisterForAssessment
from ninefruits.assessment.enums import AssessmentRegistrationStatus, ResultSource
from ninefruits.assessment.models import (
    AssessmentComponentScore,
    AssessmentRegistration,
    AssessmentResult,
    AssessmentSession,
    AssessmentType,
)
from ninefruits.curriculum.enums import ProgramRole, RequirementKind
from ninefruits.curriculum.models import CurriculumRequirement, CurriculumRequirementSet
from ninefruits.person.enums import StudentStatus
from ninefruits.person.models import StudentRecord
from ninefruits.setup import conf
from ninefruits.setup.seeders.base import Seeder

from .options import current_options

BATCH = 2000
#: Students the original chose (small size); the sessions take slices of them.
FULL_SELECTION = 40
VENUE = "Main Hall 101"
REQUIREMENT_NAME = {
    "en": "English comprehensive examination",
    "ko": "영어종합시험 합격",
    "zh-hans": "英语综合考试合格",
    "lo": "ຜ່ານການສອບເສັງພາສາອັງກິດລວມ",
}


def _user(local: str) -> Any:
    from ninefruits.security.models import User

    return User.objects.filter(email=f"{local}@{conf.DEMO_EMAIL_DOMAIN}").first()


def _months_before(day: date, months: int) -> date:
    """``CarbonImmutable::subMonths`` without overflow (31 March minus one month is 28/29 February)."""
    month_index = day.year * 12 + day.month - 1 - months
    year, month = divmod(month_index, 12)
    month += 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def _at(day: Any) -> datetime:
    return timezone.make_aware(datetime.combine(day, time(10, 0)))


class DemoAssessmentSeeder(Seeder):
    def run(self) -> None:
        registrar = _user("registrar")
        kinds = {kind.code: kind for kind in AssessmentType.objects.filter(code__in=["ENG_COMP", "COMP_EXAM", "TOPIK"])}
        english, computer, topik = kinds.get("ENG_COMP"), kinds.get("COMP_EXAM"), kinds.get("TOPIK")
        if registrar is None or english is None or computer is None or topik is None:
            return
        if AssessmentSession.objects.exists():
            return

        options = current_options()
        rng = options.rng
        records = list(StudentRecord.objects.filter(status=StudentStatus.ENROLLED).order_by("pk"))
        rng.shuffle(records)
        students = records[: options.scale(FULL_SELECTION)]
        today = timezone.localdate()
        now = timezone.now().replace(microsecond=0)
        components = english.ordered_components()

        registrations: list[AssessmentRegistration] = []
        planned: list[tuple[AssessmentRegistration, AssessmentSession, dict[int, Decimal] | None, bool | None]] = []

        sessions: list[AssessmentSession] = []
        for index, held in enumerate((_months_before(today, 7), _months_before(today, 1))):
            session = AssessmentSession.objects.create(
                assessment_type=english,
                held_date=held,
                venue=VENUE,
                registration_opens_at=_at(held - timedelta(weeks=4)),
                registration_closes_at=_at(held - timedelta(weeks=1)),
                capacity=200,
            )
            sessions.append(session)
            # Past sessions: registrations are written directly (nobody registers after the date).
            for student in self._slice(students, index * 10, 20):
                absent = rng.randint(1, 12) == 1
                registration = AssessmentRegistration(
                    session=session,
                    student_record=student,
                    status=AssessmentRegistrationStatus.ABSENT if absent else AssessmentRegistrationStatus.REGISTERED,
                    registered_at=_at(held - timedelta(weeks=2)),
                    registered_by=registrar,
                )
                registrations.append(registration)
                if absent:
                    continue
                scores = {component.pk: Decimal(rng.randint(8, 25)) for component in components}
                planned.append((registration, session, scores, None))

        computer_session = AssessmentSession.objects.create(
            assessment_type=computer, held_date=_months_before(today, 2), venue="Computer Lab B"
        )
        sessions.append(computer_session)
        for student in self._slice(students, 5, 15):
            registration = AssessmentRegistration(
                session=computer_session,
                student_record=student,
                registered_at=_at(_months_before(today, 3)),
                registered_by=registrar,
            )
            registrations.append(registration)
            planned.append((registration, computer_session, None, rng.randint(1, 5) != 1))

        AssessmentRegistration.objects.bulk_create(registrations, batch_size=BATCH)
        self._write_results(planned, english, registrar, now)

        actions = RecordAssessmentResult()
        for session in sessions:
            actions.publish(session, registrar)

        upcoming = AssessmentSession.objects.create(
            assessment_type=english,
            held_date=today + timedelta(weeks=5),
            venue=VENUE,
            registration_opens_at=now - timedelta(days=3),
            registration_closes_at=now + timedelta(weeks=3),
            capacity=150,
        )
        register = RegisterForAssessment()
        for student in self._slice(students, 25, 6):
            register.register(upcoming, student, registrar, by_staff=True)

        for index, student in enumerate(self._slice(students, 0, 4)):
            level = 3 + index % 4
            actions.external(
                student,
                topik,
                _months_before(today, 3 + index),
                True,
                registrar,
                150 + level * 30,
                f"TOPIK {level}",
                f"TOPIK-{today.year}-{1000 + index:06d}",
            )

        # The English exam is a graduation requirement in every primary curriculum.
        CurriculumRequirement.objects.bulk_create(
            CurriculumRequirement(
                requirement_set=requirement_set,
                kind=RequirementKind.ASSESSMENT_PASS,
                assessment_type=english,
                name=REQUIREMENT_NAME,
                sort_order=90,
            )
            for requirement_set in CurriculumRequirementSet.objects.filter(program_role=ProgramRole.PRIMARY).order_by(
                "pk"
            )
        )

    @staticmethod
    def _slice(items: list[Any], offset: int, length: int) -> list[Any]:
        """PHP ``Collection::slice($offset, $length)`` of the 40 chosen students (small size and
        up). With fewer students (``--size=tiny``) the same proportions, at least one each."""
        if len(items) < FULL_SELECTION:
            offset = offset * len(items) // FULL_SELECTION
            length = max(1, length * len(items) // FULL_SELECTION)
        return items[offset : offset + length]

    @staticmethod
    def _write_results(
        planned: list[tuple[AssessmentRegistration, AssessmentSession, dict[int, Decimal] | None, bool | None]],
        english: AssessmentType,
        registrar: Any,
        now: datetime,
    ) -> None:
        minimums = {c.pk: c.min_score for c in english.ordered_components() if c.min_score is not None}
        results: list[AssessmentResult] = []
        scores_of: list[dict[int, Decimal]] = []
        for registration, session, scores, decision in planned:
            if scores is not None:
                total = sum(scores.values(), Decimal(0))
                pass_score = session.pass_score if session.pass_score is not None else english.pass_score
                passed = (pass_score is not None and total >= pass_score) and all(
                    scores.get(component_id, Decimal(0)) >= minimum for component_id, minimum in minimums.items()
                )
            else:
                total, passed = None, bool(decision)
            results.append(
                AssessmentResult(
                    student_record_id=registration.student_record_id,
                    assessment_type_id=session.assessment_type_id,
                    session=session,
                    registration=registration,
                    source=ResultSource.SESSION,
                    taken_date=session.held_date,
                    total_score=total,
                    is_passed=passed,
                    entered_by=registrar,
                    entered_at=now,
                )
            )
            scores_of.append(scores or {})
        AssessmentResult.objects.bulk_create(results, batch_size=BATCH)
        AssessmentComponentScore.objects.bulk_create(
            (
                AssessmentComponentScore(result=result, component_id=component_id, score=score)
                for result, scores in zip(results, scores_of, strict=True)
                for component_id, score in scores.items()
            ),
            batch_size=BATCH,
        )
