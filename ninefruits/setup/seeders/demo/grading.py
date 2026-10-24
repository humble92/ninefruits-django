"""Demo grades (original ``DemoGradeHistorySeeder`` and ``DemoGradingSeeder``).

``DemoGradeHistorySeeder`` (before the registration demo, so registering a failed course again
becomes a retake): last term's sections copied from the current term, finalized grades for the
students (a few struggling ones get an academic warning, a few top ones honors), then term
records, standing and honors as term close makes them. The original created each enrollment with
a factory; here they are decided in memory and written with bulk inserts, and the term records
are calculated in bulk (``CloseTerm.close_records``), so ``--size=large`` stays fast.

``DemoGradingSeeder`` (after the registration demo): grade entry in the current term — every
third section evaluated relatively, a grade entry window open now, one absolute section with
every score submitted (ready to finalize), one relative section half done as drafts, and a
pending grade change request on last term's grades by its instructor. These go through the
actions, like staff would."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Any

from django.db.models import F
from django.utils import timezone

from ninefruits.core.targeting import TargetCriteria
from ninefruits.curriculum.enums import GradingBasis
from ninefruits.grading.enums import EvaluationMethod, GradeAppliesTo, GradeStatus
from ninefruits.grading.models import GradeChangeRequest, GradeScale, GradeScaleItem
from ninefruits.offering.enums import SectionStatus
from ninefruits.offering.models import Section
from ninefruits.person.enums import StudentStatus
from ninefruits.person.models import StudentRecord
from ninefruits.registration.enums import EnrollmentSource, EnrollmentStatus
from ninefruits.registration.models import Enrollment
from ninefruits.setup import conf
from ninefruits.setup.seeders.base import Seeder
from ninefruits.term.enums import TermStatus, TermWindowType
from ninefruits.term.models import Term, TermWindow

from .options import current_options

REASON = "Demo data"
BATCH = 2000
PER_STUDENT = 5

#: grade -> weight
GRADES = {"A+": 10, "A0": 15, "B+": 20, "B0": 20, "C+": 12, "C0": 8, "D+": 5, "D0": 4, "F": 6}
STRUGGLING = {"C0": 2, "D+": 3, "D0": 3, "F": 4}
TOP = {"A+": 6, "A0": 3, "B+": 1}


def _user(local: str) -> Any:
    from ninefruits.security.models import User

    return User.objects.filter(email=f"{local}@{conf.DEMO_EMAIL_DOMAIN}").first()


def _current_term() -> Term | None:
    today = timezone.localdate()
    return Term.objects.filter(status=TermStatus.PUBLISHED, start_date__lte=today).order_by("-start_date").first()


class DemoGradeHistorySeeder(Seeder):
    def run(self) -> None:
        past = (
            Term.objects.select_related("term_type")
            .filter(status=TermStatus.GRADES_CLOSED)
            .order_by("-start_date")
            .first()
        )
        current = _current_term()
        planner = _user("academic-affairs")
        scale = GradeScale.objects.filter(is_default=True).first()
        if past is None or current is None or planner is None or scale is None:
            return
        if Section.objects.filter(term=past).exists():
            return

        from ninefruits.offering.actions import CopySections

        CopySections()(current, past, planner)
        Section.objects.filter(term=past).update(status=SectionStatus.PUBLISHED)
        sections = list(
            Section.objects.filter(term=past)
            .select_related("course", "version")
            .order_by("course__code", "section_code")
        )
        if not sections:
            return

        options = current_options()
        rng = options.rng
        records = list(StudentRecord.objects.filter(status=StudentStatus.ENROLLED).order_by("student_number"))
        rng.shuffle(records)
        students = records[: options.scale(80)]

        from .registration import DemoRegistrationSeeder

        subjects = DemoRegistrationSeeder._subjects(students)
        items = {item.code: item for item in GradeScaleItem.objects.filter(grade_scale=scale)}
        pass_fail = self._pass_fail(items)
        seats = {section.pk: 0 for section in sections}
        enrolled_at = datetime.combine(
            past.start_date - timedelta(days=10), time(9), tzinfo=timezone.get_default_timezone()
        )
        finalized_at = datetime.combine(
            past.end_date + timedelta(days=7), time(17), tzinfo=timezone.get_default_timezone()
        )
        rows: list[Enrollment] = []
        graded: list[int] = []
        for index, record in enumerate(students):
            weights = STRUGGLING if index % 15 == 0 else TOP if index % 15 in (1, 8) else GRADES
            weights = {code: weight for code, weight in weights.items() if code in items} or {
                code: 1 for code, item in items.items() if item.counts_in_gpa
            }
            taken: set[int] = set()
            order = list(sections)
            rng.shuffle(order)
            for section in order:
                if len(taken) >= PER_STUDENT:
                    break
                if seats[section.pk] >= section.capacity or section.course_id in taken:
                    continue
                if not section.admits(subjects[record.pk]):
                    continue
                code = self._grade(rng, weights, section, pass_fail)
                item = items[code]
                rows.append(
                    Enrollment(
                        student_record_id=record.pk,
                        section_id=section.pk,
                        term_id=past.pk,
                        course_id=section.course_id,
                        version_id=section.version_id,
                        credits=section.version.credits,
                        category_id=section.version.category_id,
                        counts_toward_credit_limit=section.version.counts_toward_credit_limit,
                        status=EnrollmentStatus.COMPLETED,
                        source=EnrollmentSource.STAFF,
                        enrolled_at=enrolled_at,
                        grade_status=GradeStatus.FINALIZED,
                        grade_code=code,
                        grade_scale_id=scale.pk,
                        grade_points=item.grade_points,
                        counts_in_gpa=item.counts_in_gpa,
                        is_passed=item.is_passing,
                        grade_entered_at=finalized_at,
                        grade_submitted_at=finalized_at,
                        grade_finalized_at=finalized_at,
                        created_at=enrolled_at,
                        updated_at=finalized_at,
                    )
                )
                seats[section.pk] += 1
                taken.add(section.course_id)
            if taken:
                graded.append(record.pk)

        Enrollment.objects.bulk_create(rows, batch_size=BATCH)
        for section_id, count in seats.items():
            if count:
                Section.objects.filter(pk=section_id).update(enrolled_count=F("enrolled_count") + count)

        from ninefruits.grading.actions import CloseTerm

        close = CloseTerm()
        for start in range(0, len(graded), 500):
            close.close_records(past, graded[start : start + 500])
        close.finish(past, None, REASON)

    @staticmethod
    def _pass_fail(items: dict[str, GradeScaleItem]) -> tuple[str | None, str | None]:
        """The passing and failing grades of pass/fail courses on the scale (P, NP or N)."""
        candidates = [item for item in items.values() if item.applies_to == GradeAppliesTo.PASS_FAIL]
        passing = next((item.code for item in candidates if item.is_passing), None)
        failing = next((item.code for item in candidates if not item.is_passing), None)
        return passing, failing

    @staticmethod
    def _grade(rng: Any, weights: dict[str, int], section: Section, pass_fail: tuple[str | None, str | None]) -> str:
        passing, failing = pass_fail
        if section.version.grading_basis == GradingBasis.PASS_FAIL and passing is not None:
            return failing if failing is not None and rng.randint(1, 10) == 1 else passing
        roll = rng.randint(1, sum(weights.values()))
        for code, weight in weights.items():
            roll -= weight
            if roll <= 0:
                return code
        return next(iter(weights))


class DemoGradingSeeder(Seeder):
    def run(self) -> None:
        from ninefruits.grading.actions import SaveGrades
        from ninefruits.grading.services import GradeOptions

        registrar = _user("registrar")
        current = _current_term()
        if registrar is None or current is None or GradeChangeRequest.objects.exists():
            return

        now = timezone.now().replace(microsecond=0)
        TermWindow.objects.create(
            term=current,
            session=current.full_term_session(),
            window_type=TermWindowType.GRADE_ENTRY,
            name={"en": "Demo grade entry", "ko": "시연용 성적 입력", "zh-hans": "演示成绩录入"},
            opens_at=now - timedelta(days=1),
            closes_at=now + timedelta(days=14),
            eligibility=TargetCriteria.everyone(),
        )

        # Every third section of the term is evaluated relatively (grades), the rest absolutely.
        relative = [pk for pk in Section.objects.filter(term=current).values_list("pk", flat=True) if pk % 3 == 0]
        Section.objects.filter(pk__in=relative).update(evaluation_method=EvaluationMethod.RELATIVE)

        rng = current_options().rng
        options = GradeOptions()
        saver = SaveGrades(options)
        instructor = _user("instructor")

        def candidate(method: EvaluationMethod) -> Section | None:
            sections = Section.objects.filter(term=current, enrolled_count__gt=0, evaluation_method=method)
            if instructor is not None and instructor.person_id is not None:
                sections = sections.exclude(pk__in=Section.objects.taught_by(instructor.person_id).values("pk"))
            return sections.select_related("course", "version", "session").order_by("pk").first()

        # An absolutely evaluated section submitted with scores, a relative one half done.
        chosen = [candidate(EvaluationMethod.ABSOLUTE), candidate(EvaluationMethod.RELATIVE)]
        for index, section in enumerate(chosen):
            if section is None:
                continue
            entered: dict[int, dict[str, str]] = {}
            enrollments = (
                Enrollment.objects.filter(section=section, status=EnrollmentStatus.ENROLLED)
                .select_related("version", "section")
                .order_by("pk")
            )
            for position, enrollment in enumerate(enrollments):
                if index == 1 and position % 2 == 1:
                    continue  # the second section is half done
                if options.takes_score(enrollment):
                    entered[enrollment.pk] = {"score": str(rng.randint(55, 99))}
                else:
                    codes = options.codes_for(enrollment)
                    entered[enrollment.pk] = {"grade_code": codes[rng.randrange(len(codes))]}
            saver.save(section, entered, registrar)
            if index == 0:
                saver.submit(section, registrar)

        self.change_request(options)

    @staticmethod
    def change_request(options: Any) -> None:
        """Step by step (the original's nested query over sections, instructors, people and users
        was slow under row level security)."""
        from ninefruits.grading.actions import ManageGradeChanges
        from ninefruits.person.models import Instructor
        from ninefruits.security.models import User

        requester = User.objects.filter(person_id__in=Instructor.objects.values("person_id")).order_by("pk").first()
        if requester is None:
            return
        section_ids = list(Section.objects.taught_by(requester.person_id).values_list("pk", flat=True))
        enrollment = (
            Enrollment.objects.filter(
                section_id__in=section_ids, grade_status=GradeStatus.FINALIZED, grade_points__isnull=False
            )
            .select_related("version", "section")
            .order_by("pk")
            .first()
        )
        if enrollment is None:
            return
        reason = "The final project was graded before the late submission was added."
        changes = ManageGradeChanges(options)
        if options.takes_score(enrollment):
            score = (enrollment.score if enrollment.score is not None else 80) + 5
            changes.request(enrollment, None, reason, requester, str(min(score, 100)))
        else:
            changes.request(enrollment, "B+" if enrollment.grade_code == "A0" else "A0", reason, requester)
