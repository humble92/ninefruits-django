"""Demo admissions (original ``DemoAdmissionSeeder``): a regular cycle for next year and a rolling
cycle, with applications in every status (bulk inserts), plus fixed portal accounts:

- ``applicant@demo.test``: a submitted application waiting for a decision
- ``admitted@demo.test``: a released offer to accept or decline"""

from __future__ import annotations

from datetime import timedelta

from django.db import connection
from django.utils import timezone

from ninefruits.admission.enums import ApplicationStatus
from ninefruits.admission.models import (
    DOCUMENT_TYPE_LOOKUP,
    AdmissionCycle,
    AdmissionCycleDocumentType,
    AdmissionCycleProgram,
    Application,
)
from ninefruits.institution.models import LookupValue
from ninefruits.organization.models import Program
from ninefruits.person.models import Person
from ninefruits.security.models import User
from ninefruits.setup import conf
from ninefruits.setup.seeders.base import Seeder

from .options import current_options
from .people import _Names

BATCH = 1000
#: Status of the generated applications, in turn (original ``$states``).
STATES = ("submitted", "submitted", "admitted", "rejected", "confirmed", "draft")
SCHOOLS = ("Hanbit High School", "Saebom High School", "Riverside High School", "Seoul Global High School")

_SEQUENCE_SQL = (
    "INSERT INTO application_number_sequences (admission_cycle_id, last_value) VALUES (%s, %s) "
    "ON CONFLICT (admission_cycle_id) DO UPDATE SET last_value = GREATEST(application_number_sequences.last_value, "
    "EXCLUDED.last_value)"
)


class DemoAdmissionSeeder(Seeder):
    #: Local part -> description.
    ACCOUNTS: dict[str, str] = {
        "applicant": "Applicant waiting for a decision",
        "admitted": "Admitted applicant who can accept the offer",
    }

    def run(self) -> None:
        if AdmissionCycle.objects.filter(code__startswith="DEMO-").exists():
            return
        programs = list(Program.objects.effective_on().order_by("code"))
        if not programs:
            return
        options = current_options()
        self.rng = options.rng
        self.names = _Names(options.rng)
        self.now = timezone.now().replace(microsecond=0)
        self.numbers: dict[int, int] = {}
        documents = list(
            LookupValue.objects.of_type(DOCUMENT_TYPE_LOOKUP)
            .filter(code__in=["diploma", "transcript"])
            .order_by("sort_order")
        )
        year = timezone.localdate().year + 1

        regular = AdmissionCycle.objects.create(
            code=f"DEMO-{year}-REG",
            name={"en": f"{year} regular admission", "ko": f"{year}학년도 정시 모집", "zh-hans": f"{year}年常规招生"},
            opens_at=self.now - timedelta(days=30),
            closes_at=self.now + timedelta(days=30),
            is_published=True,
            offer_response_days=14,
        )
        rolling = AdmissionCycle.objects.create(
            code="DEMO-ROLLING",
            name={"en": "Rolling admission", "ko": "상시 모집", "zh-hans": "常年招生"},
            opens_at=self.now - timedelta(days=365),
            closes_at=None,
            is_published=True,
            should_release_decisions_immediately=True,
        )
        offered = {regular.pk: programs, rolling.pk: programs[:2]}
        AdmissionCycleProgram.objects.bulk_create(
            [
                AdmissionCycleProgram(admission_cycle_id=cycle_id, program=program)
                for cycle_id, cycle_programs in offered.items()
                for program in cycle_programs
            ]
        )
        AdmissionCycleDocumentType.objects.bulk_create(
            [AdmissionCycleDocumentType(admission_cycle=regular, document_type=document) for document in documents]
            + [
                AdmissionCycleDocumentType(admission_cycle=rolling, document_type=document)
                for document in documents[:1]
            ]
        )

        count = options.scale(30)
        people = [
            self.names.person(f"applicant{index + 1:05d}@{conf.DEMO_EMAIL_DOMAIN}", timezone.localdate())
            for index in range(count)
        ]
        Person.objects.bulk_create(people, batch_size=BATCH)
        rows = []
        for index, person in enumerate(people):
            cycle = rolling if index % 5 == 0 else regular
            program = self.rng.choice(offered[cycle.pk])
            rows.append(self._application(cycle, program, person, STATES[index % len(STATES)]))

        domain = conf.DEMO_EMAIL_DOMAIN
        applicant = self._account_person(f"applicant@{domain}")
        rows.append(self._application(regular, programs[0], applicant, "submitted"))
        admitted = self._account_person(f"admitted@{domain}")
        offer = self._application(regular, programs[0], admitted, "admitted", released=True)
        offer.offer_expires_at = self.now + timedelta(days=14)
        rows.append(offer)
        Application.objects.bulk_create(rows, batch_size=BATCH)

        with connection.cursor() as cursor:
            for cycle_id, last in self.numbers.items():
                cursor.execute(_SEQUENCE_SQL, [cycle_id, last])
        self._accounts([applicant, admitted])

    def _application(
        self, cycle: AdmissionCycle, program: Program, person: Person, state: str, *, released: bool = False
    ) -> Application:
        application = Application(
            admission_cycle=cycle,
            person=person,
            program=program,
            org_unit_id=program.org_unit_id,
            status=ApplicationStatus.DRAFT,
            previous_school_name=self.rng.choice(SCHOOLS),
            previous_graduation_date=timezone.localdate() - timedelta(days=30 * self.rng.randint(1, 30)),
            personal_statement="I would like to study in this program because it matches my interests and goals.",
        )
        if state == "draft":
            return application
        number = self.numbers.get(cycle.pk, 0) + 1
        self.numbers[cycle.pk] = number
        application.application_number = f"{cycle.code}-{number:05d}"
        application.submitted_at = self.now - timedelta(days=self.rng.randint(1, 20))
        application.status = ApplicationStatus.SUBMITTED
        if state in ("admitted", "rejected", "confirmed"):
            application.status = ApplicationStatus.REJECTED if state == "rejected" else ApplicationStatus.ADMITTED
            application.review_started_at = self.now - timedelta(days=2)
            application.decided_at = self.now - timedelta(days=1)
            if state == "rejected":
                application.decision_note = "Capacity"
        # Rejections and accepted offers are released; other decisions wait for the release.
        if released or state in ("rejected", "confirmed"):
            application.decision_released_at = self.now - timedelta(hours=2)
        if state == "confirmed":
            application.status = ApplicationStatus.CONFIRMED
            application.responded_at = self.now - timedelta(hours=1)
        return application

    def _account_person(self, email: str) -> Person:
        person = self.names.person(email, timezone.localdate())
        person.save()
        return person

    @staticmethod
    def _accounts(people: list[Person]) -> None:
        for person in people:
            user = User.objects.create_user(email=str(person.email), password=conf.DEMO_PASSWORD, person=person)
            user.email_verified_at = timezone.now().replace(microsecond=0)
            user.save(update_fields=["email_verified_at", "updated_at"])

    @classmethod
    def emails(cls) -> list[str]:
        return [f"{local}@{conf.DEMO_EMAIL_DOMAIN}" for local in cls.ACCOUNTS]


def demo_admission_emails() -> list[str]:
    return DemoAdmissionSeeder.emails()
