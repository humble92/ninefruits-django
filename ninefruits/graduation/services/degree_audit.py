"""The degree audit (original ``App\\Domain\\Graduation\\Services\\DegreeAudit``, ADR 0016).

Judges a student against the requirement set of their catalog year (legacy report_chkgrad only
printed the credits; the decision was a signature). Passed enrollments of every record of the
person count, equivalent courses are accepted as of the term they were taken, and waived
requirements count as satisfied."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from django.utils.translation import gettext

from ninefruits.curriculum.enums import ProgramRole, RequirementKind
from ninefruits.graduation.data import DegreeAuditResult, RequirementResult
from ninefruits.graduation.settings import GraduationSettings

ONE_DECIMAL = Decimal("0.1")


def number_text(value: Decimal | float | None) -> str:
    """Numbers in messages as the original printed PHP floats: ``12`` and ``2.5``, ``-`` for none."""
    if value is None:
        return "-"
    number = Decimal(str(value))
    if number == number.to_integral_value():
        return str(int(number))
    return format(number.normalize(), "f")


def credit_sum(enrollments: list[Any]) -> Decimal:
    return sum((Decimal(enrollment.credits) for enrollment in enrollments), Decimal("0")).quantize(ONE_DECIMAL)


class DegreeAudit:
    def __init__(
        self,
        history: Any | None = None,
        assessments: Any | None = None,
        settings: GraduationSettings | None = None,
    ) -> None:
        from ninefruits.assessment.services import AssessmentPassCheck
        from ninefruits.registration.services.course_history import CourseHistory

        self.history = history or CourseHistory()
        self.assessments = assessments or AssessmentPassCheck()
        self._settings = settings
        self._accepted_cache: dict[tuple[int, Any], list[int]] = {}

    @property
    def settings(self) -> GraduationSettings:
        if self._settings is None:
            self._settings = GraduationSettings.load()
        return self._settings

    def evaluate_all(self, record: Any) -> list[DegreeAuditResult]:
        """The primary program first, then the student's current second majors and minors."""
        from ninefruits.person.enums import AdditionalProgramRole
        from ninefruits.person.models import StudentRecordProgram

        results = [self.evaluate(record, record.program, ProgramRole.PRIMARY)]
        additional = (
            StudentRecordProgram.objects.filter(student_record_id=record.pk, end_date__isnull=True)
            .select_related("program")
            .order_by("start_date", "id")
        )
        for program in additional:
            role = ProgramRole.MINOR if program.role == AdditionalProgramRole.MINOR else ProgramRole.SECOND_MAJOR
            results.append(self.evaluate(record, program.program, role))
        return results

    def evaluate(self, record: Any, program: Any, role: ProgramRole | str) -> DegreeAuditResult:
        from ninefruits.curriculum.models import CurriculumRequirementSet
        from ninefruits.grading.models import TermRecord
        from ninefruits.graduation.models import DegreeRequirementWaiver

        role = ProgramRole(role)
        requirement_set = (
            CurriculumRequirementSet.objects.filter(program_id=program.pk, program_role=role)
            .for_catalog_year(record.catalog_year)
            .prefetch_related("requirements__courses", "requirements__assessment_type")
            .first()
        )
        passed = self._passed_enrollments(record)
        earned = credit_sum(passed)
        gpa = (
            TermRecord.objects.filter(student_record_id=record.pk)
            .order_by("-term_id")
            .values_list("cumulative_gpa", flat=True)
            .first()
        )
        gpa = None if gpa is None else Decimal(gpa)
        minimum = self.settings.minimum_cumulative_gpa if role == ProgramRole.PRIMARY else None
        minimum_gpa = None if minimum is None else Decimal(str(minimum))
        issues: list[str] = []
        requirements: list[RequirementResult] = []
        required_total: Decimal | None = None

        if requirement_set is None:
            issues.append(
                gettext("No graduation requirements are defined for catalog year %(year)s.")
                % {"year": record.catalog_year}
            )
        else:
            waived = set(
                DegreeRequirementWaiver.objects.filter(student_record_id=record.pk)
                .approved()
                .values_list("requirement_id", flat=True)
            )
            for requirement in requirement_set.requirements.all():
                result = self._judge(record, requirement, passed, requirement.pk in waived)
                requirements.append(result)
                if not result.is_satisfied:
                    issues.append(gettext("Requirement not met: %(name)s") % {"name": result.name})
            if requirement_set.total_credits is not None:
                required_total = Decimal(requirement_set.total_credits)
                if earned < required_total:
                    issues.append(
                        gettext("Total credits %(earned)s of %(required)s required.")
                        % {"earned": number_text(earned), "required": number_text(required_total)}
                    )

        if minimum_gpa is not None and (gpa is None or gpa < minimum_gpa):
            issues.append(
                gettext("Cumulative GPA %(gpa)s below the minimum %(minimum)s.")
                % {"gpa": number_text(gpa), "minimum": number_text(minimum_gpa)}
            )

        return DegreeAuditResult(
            program=program,
            role=role,
            requirement_set=requirement_set,
            earned_credits=earned,
            required_credits=required_total,
            cumulative_gpa=gpa,
            minimum_gpa=minimum_gpa,
            requirements=requirements,
            issues=issues,
        )

    # -- requirements ------------------------------------------------------------------------------
    def _judge(self, record: Any, requirement: Any, passed: list[Any], waived: bool) -> RequirementResult:
        kind = RequirementKind(requirement.kind)
        name = str(requirement.name) if requirement.name else str(kind.label)
        required = None if requirement.min_credits is None else Decimal(requirement.min_credits)

        if kind == RequirementKind.CATEGORY_CREDITS:
            category_ids = self._category_and_descendants(int(requirement.category_id or 0))
            counted = [enrollment for enrollment in passed if enrollment.category_id in category_ids]
            credits = credit_sum(counted)
            return RequirementResult(
                requirement.pk,
                kind,
                name,
                required,
                None,
                credits,
                len(counted),
                waived or credits >= (required or Decimal("0")),
                waived,
                self._describe(counted),
            )

        courses = list(requirement.courses.all())
        if kind == RequirementKind.REQUIRED_COURSES:
            counted, missing = [], []
            for course in courses:
                match = self._first_passed(passed, course.pk)
                if match is None:
                    missing.append(course.code)
                else:
                    counted.append(match)
            return RequirementResult(
                requirement.pk,
                kind,
                name,
                None,
                len(courses),
                credit_sum(counted),
                len(counted),
                waived or not missing,
                waived,
                self._describe(counted),
                missing,
            )

        if kind == RequirementKind.COURSE_GROUP:
            counted = [match for course in courses if (match := self._first_passed(passed, course.pk)) is not None]
            credits = credit_sum(counted)
            satisfied = (required is None or credits >= required) and (
                requirement.min_courses is None or len(counted) >= requirement.min_courses
            )
            return RequirementResult(
                requirement.pk,
                kind,
                name,
                required,
                requirement.min_courses,
                credits,
                len(counted),
                waived or satisfied,
                waived,
                self._describe(counted),
            )

        # Passed examination (ADR 0014).
        kind_of_exam = requirement.assessment_type
        passed_exam = kind_of_exam is not None and self.assessments.has_passed(record, kind_of_exam)
        return RequirementResult(
            requirement.pk,
            kind,
            name if kind_of_exam is None else str(kind_of_exam.name),
            None,
            None,
            Decimal("0"),
            1 if passed_exam else 0,
            waived or passed_exam,
            waived,
        )

    def _passed_enrollments(self, record: Any) -> list[Any]:
        """Passed enrollments of the person, across their student records, with the course and
        version."""
        from ninefruits.person.models import StudentRecord
        from ninefruits.registration.enums import EnrollmentStatus
        from ninefruits.registration.models import Enrollment

        return list(
            Enrollment.objects.filter(
                student_record_id__in=StudentRecord.objects.filter(person_id=record.person_id).values("pk"),
                status=EnrollmentStatus.COMPLETED,
                is_passed=True,
            )
            .select_related("course", "version", "term")
            .order_by("id")
        )

    def _first_passed(self, passed: list[Any], course_id: int) -> Any | None:
        """The passed enrollment in the course or in a course accepted as equivalent when it was
        taken."""
        for enrollment in passed:
            if enrollment.course_id == course_id or course_id in self._accepted(
                enrollment.course_id, enrollment.term.start_date
            ):
                return enrollment
        return None

    def _accepted(self, course_id: int, on: Any) -> list[int]:
        key = (course_id, on)
        if key not in self._accepted_cache:
            self._accepted_cache[key] = self.history.accepted_course_ids(course_id, on)
        return self._accepted_cache[key]

    @staticmethod
    def _category_and_descendants(category_id: int) -> set[int]:
        from ninefruits.curriculum.models import CourseCategory

        children: dict[int | None, list[int]] = defaultdict(list)
        for pk, parent_id in CourseCategory.objects.values_list("id", "parent_id"):
            children[parent_id].append(pk)
        ids = [category_id]
        index = 0
        while index < len(ids):
            ids.extend(children.get(ids[index], []))
            index += 1
        return set(ids)

    @staticmethod
    def _describe(enrollments: list[Any]) -> list[dict[str, Any]]:
        return [
            {
                "code": enrollment.course.code,
                "title": str(enrollment.version.title or ""),
                "credits": str(enrollment.credits),
                "grade": enrollment.grade_code,
            }
            for enrollment in sorted(enrollments, key=lambda e: e.course.code)
        ]
