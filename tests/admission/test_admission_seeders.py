"""Demo admissions (original ``DemoAdmissionSeeder``; row counts of the original small demo:
2 cycles, 7 cycle programs, 3 cycle documents, 32 applications)."""

from __future__ import annotations

import pytest

from ninefruits.admission.enums import ApplicationStatus
from ninefruits.admission.models import (
    AdmissionCycle,
    AdmissionCycleDocumentType,
    AdmissionCycleProgram,
    Application,
    ApplicationNumberSequence,
)
from ninefruits.security.models import User
from ninefruits.setup.seeders.demo.admission import DemoAdmissionSeeder
from ninefruits.setup.seeders.demo.options import DemoOptions, use_options
from ninefruits.setup.seeders.demo.reference import DemoReferenceSeeder

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("admission_reference")]


def test_seeds_the_small_demo_admissions_like_the_original_once() -> None:
    with use_options(DemoOptions("small", 42)):
        DemoReferenceSeeder()()
        DemoAdmissionSeeder()()
        DemoAdmissionSeeder()()  # idempotent

    assert AdmissionCycle.objects.count() == 2
    assert AdmissionCycleProgram.objects.count() == 7
    assert AdmissionCycleDocumentType.objects.count() == 3
    assert Application.objects.count() == 32
    statuses = set(Application.objects.values_list("status", flat=True))
    assert statuses == {
        ApplicationStatus.DRAFT,
        ApplicationStatus.SUBMITTED,
        ApplicationStatus.ADMITTED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.CONFIRMED,
    }
    # Numbers come from the per-cycle sequence, so applications submitted later continue it.
    for sequence in ApplicationNumberSequence.objects.select_related("admission_cycle"):
        numbers = Application.objects.filter(
            admission_cycle=sequence.admission_cycle, application_number__isnull=False
        ).count()
        assert sequence.last_value == numbers
    admitted = User.objects.get(email="admitted@demo.test")
    offer = Application.objects.get(person_id=admitted.person_id)
    assert offer.applicant_status() == ApplicationStatus.ADMITTED
    assert offer.offer_expires_at is not None
    assert User.objects.get(email="applicant@demo.test").has_verified_email()
