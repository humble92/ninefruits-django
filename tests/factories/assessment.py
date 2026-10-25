"""Factories for examinations (the original has none: its tests use the profile's kinds).
``AssessmentSessionFactory(open=True)`` has a registration window around now."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import factory
from django.utils import timezone

from ninefruits.assessment.enums import AssessmentCategory, AssessmentRegistrationStatus, ResultSource, ScoringMethod
from ninefruits.assessment.models import (
    AssessmentComponent,
    AssessmentRegistration,
    AssessmentResult,
    AssessmentSession,
    AssessmentType,
)

from .person import StudentRecordFactory


class AssessmentTypeFactory(factory.django.DjangoModelFactory):
    """A score kind with a pass score of 60; ``pass_fail=True`` for one staff decide."""

    class Meta:
        model = AssessmentType
        django_get_or_create = ("code",)

    class Params:
        pass_fail = factory.Trait(scoring=ScoringMethod.PASS_FAIL, pass_score=None)
        external = factory.Trait(
            category=AssessmentCategory.EXTERNAL, scoring=ScoringMethod.PASS_FAIL, pass_score=None, allows_external=True
        )

    code = factory.Sequence(lambda n: f"EXAM{n}")
    name = factory.LazyAttribute(lambda kind: {"en": f"Examination {kind.code}", "ko": f"시험 {kind.code}"})
    category = AssessmentCategory.COMPREHENSIVE
    scoring = ScoringMethod.SCORE
    pass_score = Decimal("60.0")


class AssessmentComponentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AssessmentComponent

    assessment_type = factory.SubFactory(AssessmentTypeFactory)
    code = factory.Sequence(lambda n: f"AREA{n}")
    name = factory.LazyAttribute(lambda component: {"en": component.code.title()})
    max_score = Decimal("25.0")
    sort_order = factory.Sequence(lambda n: n * 10)


class AssessmentSessionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AssessmentSession

    class Params:
        open = factory.Trait(
            registration_opens_at=factory.LazyFunction(lambda: timezone.now() - timedelta(days=1)),
            registration_closes_at=factory.LazyFunction(lambda: timezone.now() + timedelta(weeks=1)),
        )
        published = factory.Trait(results_published_at=factory.LazyFunction(timezone.now))

    assessment_type = factory.SubFactory(AssessmentTypeFactory)
    held_date = factory.Sequence(lambda n: timezone.localdate() + timedelta(days=14 + n))


class AssessmentRegistrationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AssessmentRegistration

    session = factory.SubFactory(AssessmentSessionFactory)
    student_record = factory.SubFactory(StudentRecordFactory)
    status = AssessmentRegistrationStatus.REGISTERED
    registered_at = factory.LazyFunction(lambda: timezone.now().replace(microsecond=0))


class AssessmentResultFactory(factory.django.DjangoModelFactory):
    """A session result for a registration; ``external=True`` for an outside body's result."""

    class Meta:
        model = AssessmentResult

    class Params:
        external = factory.Trait(
            registration=None,
            session=None,
            source=ResultSource.EXTERNAL,
            assessment_type=factory.SubFactory(AssessmentTypeFactory, external=True),
            student_record=factory.SubFactory(StudentRecordFactory),
            taken_date=factory.LazyFunction(lambda: timezone.localdate() - timedelta(days=30)),
        )

    registration = factory.SubFactory(AssessmentRegistrationFactory)
    session = factory.LazyAttribute(lambda result: result.registration.session if result.registration else None)
    student_record = factory.LazyAttribute(
        lambda result: result.registration.student_record if result.registration else None
    )
    assessment_type = factory.LazyAttribute(lambda result: result.session.assessment_type if result.session else None)
    source = ResultSource.SESSION
    taken_date = factory.LazyAttribute(lambda result: result.session.held_date if result.session else None)
    total_score = Decimal("70.0")
    is_passed = True
    entered_at = factory.LazyFunction(lambda: timezone.now().replace(microsecond=0))
