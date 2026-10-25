"""Demo graduation (original ``DemoGraduationSeeder``).

Degree audits for the current term's third- and fourth-year students. Three fourth-year students
(enrolled, cumulative GPA of at least 2.5) get a complete course history in the oldest closed
term (every requirement of their curriculum, then filler courses up to the total credits), a
passed English examination, and waivers for what the small demo catalog cannot satisfy (requested
by the registrar, approved by the system administrator), so satisfied audits exist; the first of
them whose stored audit is satisfied graduates with a degree number.

The passed enrollments are written with one bulk insert (a section of its own per course, so a
student who already sat the term's regular section is not counted twice); the waivers, audits
and graduation go through the actions, like staff would."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from django.db.models import F, Sum
from django.utils import timezone

from ninefruits.setup import conf
from ninefruits.setup.seeders.base import Seeder

BATCH = 2000
SENIORS = 3
SECTION_CODE = "GR"


def _user(local: str) -> Any:
    from ninefruits.security.models import User

    return User.objects.filter(email=f"{local}@{conf.DEMO_EMAIL_DOMAIN}").first()


def _months_before(day: date, months: int) -> date:
    from .assessment import _months_before as months_before

    return months_before(day, months)


class DemoGraduationSeeder(Seeder):
    def run(self) -> None:
        from ninefruits.curriculum.enums import ProgramRole
        from ninefruits.grading.models import TermRecord
        from ninefruits.graduation.actions import GraduateStudents, RunDegreeAudits
        from ninefruits.graduation.models import DegreeAudit
        from ninefruits.person.enums import StudentStatus
        from ninefruits.person.models import StudentRecord
        from ninefruits.term.enums import TermStatus
        from ninefruits.term.models import Term

        registrar = _user("registrar")
        approver = _user("system-administrator")
        today = timezone.localdate()
        current = (
            Term.objects.filter(status=TermStatus.PUBLISHED, start_date__lte=today).order_by("-start_date").first()
        )
        past = Term.objects.filter(status=TermStatus.GRADES_CLOSED).order_by("start_date").first()
        if registrar is None or approver is None or current is None or past is None or DegreeAudit.objects.exists():
            return

        seniors = list(
            StudentRecord.objects.filter(status=StudentStatus.ENROLLED, year_level=4)
            .filter(pk__in=TermRecord.objects.filter(cumulative_gpa__gte=Decimal("2.5")).values("student_record_id"))
            .select_related("program")
            .order_by("student_number")[:SENIORS]
        )
        self._complete_requirements(seniors, past)
        for record in seniors:
            self._pass_examination(record, registrar)
            self._waive_what_remains(record, registrar, approver)

        RunDegreeAudits().for_all(current, registrar, minimum_year_level=3)

        # Graduate the first senior whose stored audit is satisfied (a tiny catalog may not reach
        # the total credits).
        for record in seniors:
            latest = (
                DegreeAudit.objects.filter(student_record_id=record.pk, program_role=ProgramRole.PRIMARY)
                .order_by("-id")
                .first()
            )
            if latest is not None and latest.is_satisfied:
                GraduateStudents().handle(record, current.start_date - timedelta(days=10), registrar, "Demo graduation")
                break

    # -- course history ---------------------------------------------------------------------------
    def _complete_requirements(self, seniors: list[Any], term: Any) -> None:
        """Passed enrollments for every requirement of the primary set, then filler courses up to
        the total credits (the unit's courses first, then the rest of the catalog)."""
        from ninefruits.curriculum.enums import ProgramRole, RequirementKind
        from ninefruits.curriculum.models import Course, CourseVersion, CurriculumRequirementSet
        from ninefruits.registration.models import Enrollment

        plan: list[tuple[Any, Any]] = []
        for record in seniors:
            requirement_set = (
                CurriculumRequirementSet.objects.filter(program_id=record.program_id, program_role=ProgramRole.PRIMARY)
                .for_catalog_year(record.catalog_year)
                .prefetch_related("requirements__courses")
                .first()
            )
            if requirement_set is None:
                continue
            passed_rows = Enrollment.objects.filter(student_record_id=record.pk, is_passed=True)
            passed = set(passed_rows.values_list("course_id", flat=True))
            credits = Decimal(passed_rows.aggregate(total=Sum("credits"))["total"] or 0)

            for requirement in requirement_set.requirements.all():
                kind = RequirementKind(requirement.kind)
                if kind == RequirementKind.CATEGORY_CREDITS:
                    picked, total = [], Decimal("0")
                    versions = (
                        CourseVersion.objects.filter(category_id=requirement.category_id)
                        .select_related("course")
                        .order_by("course_id", "effective_start_date")
                    )
                    for version in versions:
                        if total >= Decimal(requirement.min_credits or 0):
                            break
                        picked.append(version.course)
                        total += Decimal(version.credits)
                    courses = picked
                elif kind == RequirementKind.REQUIRED_COURSES:
                    courses = list(requirement.courses.all())
                elif kind == RequirementKind.COURSE_GROUP:
                    wanted = max(-(-int(Decimal(requirement.min_credits or 0)) // 3), int(requirement.min_courses or 0))
                    courses = list(requirement.courses.all())[:wanted]
                else:
                    courses = []
                for course in courses:
                    credits += self._take(record, course, term, passed, plan)

            total_credits = Decimal(requirement_set.total_credits or 0)
            filler = sorted(
                Course.objects.order_by("code"), key=lambda c: (c.org_unit_id != record.org_unit_id, c.code)
            )
            for course in filler:
                if credits >= total_credits:
                    break
                credits += self._take(record, course, term, passed, plan)
        self._pass(plan, term)

    def _take(self, record: Any, course: Any, term: Any, passed: set[int], plan: list[tuple[Any, Any]]) -> Decimal:
        """Plans a passed enrollment in the course unless already passed; returns its credits."""
        if course.pk in passed:
            return Decimal("0")
        version = self._version(course, term)
        if version is None:
            return Decimal("0")
        plan.append((record, course))
        passed.add(course.pk)
        return Decimal(version.credits)

    @staticmethod
    def _version(course: Any, term: Any) -> Any:
        versions = course.versions.order_by("effective_start_date")
        return versions.effective_on(term.start_date).first() or versions.first()

    def _pass(self, plan: list[tuple[Any, Any]], term: Any) -> None:
        """A-grade completed enrollments, one section per course in the term."""
        from ninefruits.grading.models import GradeScale, GradeScaleItem
        from ninefruits.offering.enums import SectionStatus
        from ninefruits.offering.models import Section
        from ninefruits.registration.enums import EnrollmentSource, EnrollmentStatus, GradeStatus
        from ninefruits.registration.models import Enrollment

        scale = GradeScale.objects.filter(is_default=True).first()
        item = GradeScaleItem.objects.filter(grade_scale=scale, code="A0").first() if scale else None
        if not plan or scale is None or item is None:
            return
        session = term.full_term_session()
        sections: dict[int, Section] = {}
        for _record, course in plan:
            if course.pk in sections:
                continue
            version = self._version(course, term)
            section = Section.objects.filter(term=term, course=course, section_code=SECTION_CODE).first()
            sections[course.pk] = section or Section.objects.create(
                term=term,
                session=session,
                course=course,
                version=version,
                section_code=SECTION_CODE,
                org_unit_id=course.org_unit_id,
                capacity=200,
                status=SectionStatus.PUBLISHED,
            )
        zone = timezone.get_default_timezone()
        enrolled_at = datetime.combine(term.start_date, time(9), tzinfo=zone)
        finalized_at = datetime.combine(term.end_date + timedelta(days=7), time(17), tzinfo=zone)
        rows = []
        for record, course in plan:
            section = sections[course.pk]
            version = section.version
            rows.append(
                Enrollment(
                    student_record_id=record.pk,
                    section_id=section.pk,
                    term_id=term.pk,
                    course_id=course.pk,
                    version_id=version.pk,
                    credits=version.credits,
                    category_id=version.category_id,
                    counts_toward_credit_limit=version.counts_toward_credit_limit,
                    status=EnrollmentStatus.COMPLETED,
                    source=EnrollmentSource.STAFF,
                    enrolled_at=enrolled_at,
                    grade_status=GradeStatus.FINALIZED,
                    grade_code=item.code,
                    grade_scale_id=scale.pk,
                    grade_points=item.grade_points,
                    counts_in_gpa=item.counts_in_gpa,
                    is_passed=True,
                    grade_entered_at=finalized_at,
                    grade_submitted_at=finalized_at,
                    grade_finalized_at=finalized_at,
                    created_at=enrolled_at,
                    updated_at=finalized_at,
                )
            )
        Enrollment.objects.bulk_create(rows, batch_size=BATCH)
        counts: dict[int, int] = {}
        for _record, course in plan:
            counts[sections[course.pk].pk] = counts.get(sections[course.pk].pk, 0) + 1
        for section_id, count in counts.items():
            Section.objects.filter(pk=section_id).update(enrolled_count=F("enrolled_count") + count)

    # -- examination and waivers --------------------------------------------------------------------
    @staticmethod
    def _pass_examination(record: Any, registrar: Any) -> None:
        """A passed English examination (the curriculum requires it): a past session with a result."""
        from ninefruits.assessment.actions import RecordAssessmentResult
        from ninefruits.assessment.models import AssessmentRegistration, AssessmentSession, AssessmentType
        from ninefruits.assessment.services import AssessmentPassCheck

        kind = AssessmentType.objects.filter(code="ENG_COMP").prefetch_related("components").first()
        if kind is None or AssessmentPassCheck().has_passed(record, kind):
            return
        held = _months_before(timezone.localdate(), 9)
        session, _created = AssessmentSession.objects.get_or_create(
            assessment_type=kind, held_date=held, defaults={"venue": "Main Hall 101"}
        )
        registration, _created = AssessmentRegistration.objects.get_or_create(
            session=session,
            student_record=record,
            defaults={
                "registered_at": timezone.make_aware(datetime.combine(held - timedelta(weeks=2), time(10))),
                "registered_by": registrar,
            },
        )
        RecordAssessmentResult().for_registration(
            registration,
            {component.code: 20 for component in kind.components.all()},
            None,
            registrar,
            applying_correction=session.results_published_at is not None,
        )

    @staticmethod
    def _waive_what_remains(record: Any, registrar: Any, approver: Any) -> None:
        """Whatever the small demo catalog cannot satisfy (a category with too few courses) is
        waived with a reason, which also shows waivers in the screens."""
        from ninefruits.curriculum.enums import ProgramRole
        from ninefruits.curriculum.models import CurriculumRequirement
        from ninefruits.graduation.actions import WaiveRequirement
        from ninefruits.graduation.services import DegreeAudit

        waive = WaiveRequirement()
        for result in DegreeAudit().evaluate(record, record.program, ProgramRole.PRIMARY).requirements:
            if not result.is_satisfied:
                requirement = CurriculumRequirement.objects.get(pk=result.requirement_id)
                waiver = waive.request(record, requirement, "Demo: transfer credit recognized", registrar)
                waive.approve(waiver, approver, "Checked the transcript")
