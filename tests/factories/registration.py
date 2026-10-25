"""Factories for registrations (original ``Database\\Factories\\Registration\\EnrollmentFactory``).

``EnrollmentFactory(section=section, student_record=record)`` copies the course snapshot from
the section (original ``inSection``). ``EnrollmentFactory(section=..., grade="B0")`` is a
completed enrollment with a finalized grade of the default scale (a 4.5 scale is created when
there is none; original ``completed('B0')``). Like the original factory, these rows do not change
the section's seat counter; registrations through ``EnrollStudent`` do."""

from __future__ import annotations

from typing import Any

import factory
from django.utils import timezone

from ninefruits.registration.enums import EnrollmentStatus, GradeStatus, WaitlistStatus
from ninefruits.registration.models import CreditLimitPolicy, Enrollment, RegistrationHold, WaitlistEntry
from tests.factories.offering import SectionFactory
from tests.factories.person import StudentRecordFactory


def _now() -> Any:
    return timezone.now().replace(microsecond=0)


def default_scale_item(grade: str) -> Any:
    from ninefruits.grading.models import GradeScale, GradeScaleItem
    from ninefruits.setup.seeders.profiles.korean_university import seed_scale_45

    scale = GradeScale.objects.filter(is_default=True).first() or seed_scale_45(True)
    return scale, GradeScaleItem.objects.filter(grade_scale=scale, code=grade).first()


class EnrollmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Enrollment

    class Params:
        grade: str | None = None
        passed: bool | None = None
        scale_item = factory.LazyAttribute(lambda o: default_scale_item(o.grade) if o.grade else (None, None))

    student_record = factory.SubFactory(StudentRecordFactory)
    section = factory.SubFactory(SectionFactory, published=True)
    term = factory.LazyAttribute(lambda o: o.section.term)
    course = factory.LazyAttribute(lambda o: o.section.course)
    version = factory.LazyAttribute(lambda o: o.section.version)
    credits = factory.LazyAttribute(lambda o: o.section.version.credits)
    category = factory.LazyAttribute(lambda o: o.section.version.category)
    counts_toward_credit_limit = factory.LazyAttribute(lambda o: o.section.version.counts_toward_credit_limit)
    enrolled_at = factory.LazyFunction(_now)
    status = factory.LazyAttribute(lambda o: EnrollmentStatus.COMPLETED if o.grade else EnrollmentStatus.ENROLLED)
    grade_status = factory.LazyAttribute(lambda o: GradeStatus.FINALIZED if o.grade else GradeStatus.NONE)
    grade_code = factory.LazyAttribute(lambda o: o.grade)
    grade_scale = factory.LazyAttribute(lambda o: o.scale_item[0])
    grade_points = factory.LazyAttribute(lambda o: o.scale_item[1].grade_points if o.scale_item[1] else None)
    counts_in_gpa = factory.LazyAttribute(
        lambda o: (o.scale_item[1].counts_in_gpa if o.scale_item[1] else False) if o.grade else None
    )
    is_passed = factory.LazyAttribute(
        lambda o: (
            None
            if not o.grade
            else o.passed
            if o.passed is not None
            else (o.scale_item[1].is_passing if o.scale_item[1] else True)
        )
    )
    grade_finalized_at = factory.LazyAttribute(lambda o: _now() if o.grade else None)


class WaitlistEntryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WaitlistEntry

    section = factory.SubFactory(SectionFactory, published=True)
    student_record = factory.SubFactory(StudentRecordFactory)
    status = WaitlistStatus.WAITING
    requested_at = factory.LazyFunction(_now)


class RegistrationHoldFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RegistrationHold

    student_record = factory.SubFactory(StudentRecordFactory)
    hold_type = "financial"
    starts_at = factory.LazyFunction(_now)
    reason = "Test hold"


class CreditLimitPolicyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CreditLimitPolicy

    name = factory.Sequence(lambda n: {"en": f"Limit {n}"})
    max_credits = 18
