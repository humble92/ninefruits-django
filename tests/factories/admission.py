"""Factories for admission cycles and applications (original ``Database\\Factories\\Admission``).

    AdmissionCycleFactory(programs=[program], documents=[diploma])   # published, open since last month
    AdmissionCycleFactory(rolling=True) / AdmissionCycleFactory(closed=True)
    ApplicationFactory(admission_cycle=cycle, program=program)       # draft
    ApplicationFactory(..., submitted=True | admitted=True | rejected=True | confirmed=True, released=True)

The later states are set directly (without notifications), for fixtures and demo data."""

from __future__ import annotations

import itertools
import random
from collections.abc import Iterable
from datetime import timedelta
from typing import Any

import factory
from django.utils import timezone

from ninefruits.admission.enums import ApplicationStatus
from ninefruits.admission.models import AdmissionCycle, AdmissionCycleDocumentType, AdmissionCycleProgram, Application

from .organization import ProgramFactory
from .person import PersonFactory

_numbers = itertools.count(90000)


class AdmissionCycleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AdmissionCycle
        skip_postgeneration_save = True

    class Params:
        year = factory.LazyFunction(lambda: timezone.localdate().year + 1)
        rolling = factory.Trait(closes_at=None, should_release_decisions_immediately=True)
        closed = factory.Trait(
            opens_at=factory.LazyFunction(lambda: timezone.now() - timedelta(days=90)),
            closes_at=factory.LazyFunction(lambda: timezone.now() - timedelta(days=30)),
        )

    code = factory.Sequence(lambda n: f"AD{timezone.localdate().year + 1}-{n:03d}")
    name = factory.LazyAttribute(
        lambda cycle: {
            "en": f"{cycle.year} regular admission",
            "ko": f"{cycle.year}학년도 정시 모집",
            "zh-hans": f"{cycle.year}年常规招生",
        }
    )
    opens_at = factory.LazyFunction(lambda: timezone.now() - timedelta(days=30))
    closes_at = factory.LazyFunction(lambda: timezone.now() + timedelta(days=30))
    is_published = True

    @factory.post_generation
    def programs(self, create: bool, extracted: Iterable[Any] | None, **kwargs: Any) -> None:
        if create and extracted:
            for program in extracted:
                AdmissionCycleProgram.objects.get_or_create(admission_cycle=self, program=program)

    @factory.post_generation
    def documents(self, create: bool, extracted: Iterable[Any] | None, **kwargs: Any) -> None:
        """Required document types (lookup values)."""
        if create and extracted:
            for document_type in extracted:
                AdmissionCycleDocumentType.objects.get_or_create(
                    admission_cycle=self, document_type=document_type, defaults={"is_required": True}
                )


def _number(application: Any) -> str:
    """Same shape as ``SubmitApplication``, from a high range so it never meets real numbers."""
    return f"{application.admission_cycle.code}-{next(_numbers)}"


class ApplicationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Application
        skip_postgeneration_save = True

    class Params:
        submitted = factory.Trait(
            status=ApplicationStatus.SUBMITTED,
            application_number=factory.LazyAttribute(_number),
            submitted_at=factory.LazyFunction(lambda: timezone.now() - timedelta(days=random.randint(1, 20))),
        )
        admitted = factory.Trait(
            submitted=True,
            status=ApplicationStatus.ADMITTED,
            decided_at=factory.LazyFunction(lambda: timezone.now() - timedelta(days=1)),
            review_started_at=factory.LazyFunction(lambda: timezone.now() - timedelta(days=2)),
        )
        rejected = factory.Trait(
            submitted=True,
            status=ApplicationStatus.REJECTED,
            decided_at=factory.LazyFunction(lambda: timezone.now() - timedelta(days=1)),
            decision_note="Capacity",
            review_started_at=factory.LazyFunction(lambda: timezone.now() - timedelta(days=2)),
        )
        released = factory.Trait(decision_released_at=factory.LazyFunction(lambda: timezone.now() - timedelta(hours=2)))
        confirmed = factory.Trait(
            admitted=True,
            released=True,
            status=ApplicationStatus.CONFIRMED,
            responded_at=factory.LazyFunction(lambda: timezone.now() - timedelta(hours=1)),
        )

    admission_cycle = factory.SubFactory(AdmissionCycleFactory)
    person = factory.SubFactory(PersonFactory)
    program = factory.SubFactory(ProgramFactory)
    org_unit = factory.LazyAttribute(lambda application: application.program.org_unit)
    status = ApplicationStatus.DRAFT
    previous_school_name = factory.LazyFunction(
        lambda: f"{random.choice(['Hanbit', 'Saebom', 'Riverside'])} High School"
    )
    previous_graduation_date = factory.LazyFunction(
        lambda: timezone.localdate() - timedelta(days=30 * random.randint(1, 30))
    )
    personal_statement = factory.Faker("paragraph", nb_sentences=4)

    @factory.post_generation
    def offered(self, create: bool, extracted: Any, **kwargs: Any) -> None:
        """The program is offered in the cycle (original ``forCycle``)."""
        if create:
            AdmissionCycleProgram.objects.get_or_create(
                admission_cycle_id=self.admission_cycle_id, program=self.program
            )
