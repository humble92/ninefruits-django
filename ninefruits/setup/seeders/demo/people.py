from __future__ import annotations

import random
from collections.abc import Iterator
from datetime import date, timedelta
from typing import Any

from django.contrib.auth.hashers import make_password
from django.utils import timezone
from faker import Faker

from ninefruits.organization.models import Program
from ninefruits.person.enums import AdvisorRole, EmploymentType, Gender, GuardianRelationship, StudentStatus
from ninefruits.person.models import (
    AdvisorAssignment,
    Guardian,
    Instructor,
    Person,
    StudentRecord,
    StudentStatusChange,
    StudentStatusChangeType,
)
from ninefruits.person.services.student_numbers import StudentNumberGenerator
from ninefruits.security.models import User
from ninefruits.setup import conf
from ninefruits.setup.seeders.base import Seeder

from .options import DemoOptions, current_options

BATCH = 1000


class _Names:
    """Names from mixed locales (en_US, ko_KR, zh_CN), drawn from the demo generator so that
    ``--seed`` reproduces them (original ``PersonFactory``)."""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.fakers = {locale: Faker(locale) for locale in ("en_US", "ko_KR", "zh_CN")}
        for faker in self.fakers.values():
            faker.seed_instance(rng.randrange(2**31))

    def person(self, email: str | None, today: date) -> Person:
        locale = self.rng.choice(["en_US", "ko_KR", "zh_CN"])
        gender = self.rng.choice([Gender.FEMALE, Gender.MALE])
        english = self.fakers["en_US"]
        given = english.first_name_female() if gender == Gender.FEMALE else english.first_name_male()
        variants: dict[str, str] | None = None
        if locale == "ko_KR":
            local = self.fakers["ko_KR"]
            variants = {"ko": local.last_name() + local.first_name()}
        elif locale == "zh_CN":
            local = self.fakers["zh_CN"]
            variants = {"zh-hans": local.last_name() + local.first_name()}
        return Person(
            family_name=english.last_name(),
            given_name=given,
            name_variants=variants,
            birth_date=today - timedelta(days=self.rng.randint(18 * 365, 30 * 365)),
            gender=gender,
            email=email,
            phone=f"010-{self.rng.randint(0, 9999):04d}-{self.rng.randint(0, 9999):04d}",
        )

    def full_name(self) -> str:
        return str(self.fakers["en_US"].name())


class DemoPeopleSeeder(Seeder):
    """Instructors, students across admission years and statuses, alumni, guardians, advisors
    and pending status change requests (bulk inserts), plus fixed portal accounts:

    - ``student@demo.test``: a current student with an advisor
    - ``alumni@demo.test``: a graduate
    - ``readmitted@demo.test``: a graduate admitted again (two student records)
    - ``instructor@demo.test``: an instructor who advises students"""

    #: Local part -> description.
    ACCOUNTS: dict[str, str] = {
        "student": "Current student",
        "alumni": "Graduate",
        "readmitted": "Graduate admitted again (two records)",
        "instructor": "Instructor and advisor",
    }

    def run(self) -> None:
        if Instructor.objects.filter(employee_number__startswith="DEMO-").exists():
            return
        programs = list(
            Program.objects.effective_on()
            .filter(org_unit__in=_effective_units())
            .select_related("org_unit")
            .order_by("code")
        )
        if not programs:
            return
        options = current_options()
        self.today = timezone.localdate()
        self.names = _Names(options.rng)
        self.rng = options.rng
        self.numbers = StudentNumberGenerator()
        instructors = self.instructors(programs, options)
        self.students(programs, instructors, options)
        self.fixed_accounts(programs, instructors)

    # -- instructors ------------------------------------------------------------------------------
    def instructors(self, programs: list[Program], options: DemoOptions) -> dict[int, list[Instructor]]:
        units = list(dict.fromkeys(program.org_unit_id for program in programs))
        per_unit = max(2, options.scale(20) // len(programs))
        people = [self.names.person(None, self.today) for _ in range(per_unit * len(units))]
        Person.objects.bulk_create(people, batch_size=BATCH)
        rows: list[Instructor] = []
        sequence = 0
        for unit in units:
            for _ in range(per_unit):
                person = people[sequence]
                sequence += 1
                rows.append(
                    Instructor(
                        person=person,
                        employee_number=f"DEMO-{sequence:05d}",
                        org_unit_id=unit,
                        employment_type=self.rng.choice(
                            [
                                EmploymentType.FULL_TIME,
                                EmploymentType.FULL_TIME,
                                EmploymentType.PART_TIME,
                                EmploymentType.ADJUNCT,
                            ]
                        ),
                        academic_title={"en": "Professor", "ko": "교수", "zh-hans": "教授"},
                        hire_date=self.today - timedelta(days=self.rng.randint(365, 20 * 365)),
                    )
                )
        Instructor.objects.bulk_create(rows, batch_size=BATCH)
        by_unit: dict[int, list[Instructor]] = {}
        for instructor in rows:
            by_unit.setdefault(instructor.org_unit_id, []).append(instructor)
        return by_unit

    # -- students ---------------------------------------------------------------------------------
    def students(self, programs: list[Program], instructors: dict[int, list[Instructor]], options: DemoOptions) -> None:
        this_year = self.today.year
        leave = StudentStatusChangeType.objects.filter(code="leave_of_absence").first()
        count = options.student_count()
        plan: list[tuple[Program, int, StudentStatus]] = []
        for index in range(count):
            program = programs[index % len(programs)]
            # Admission years spread over six years; the two oldest are mostly graduates.
            year = this_year - (index % 6)
            if year <= this_year - 4:
                status = self.rng.choice([StudentStatus.GRADUATED] * 3 + [StudentStatus.WITHDRAWN])
            else:
                status = self.rng.choice(
                    [StudentStatus.ENROLLED] * 12 + [StudentStatus.ON_LEAVE, StudentStatus.WITHDRAWN]
                )
            plan.append((program, year, status))

        people = [self.names.person(None, self.today) for _ in plan]
        Person.objects.bulk_create(people, batch_size=BATCH)
        numbers = self._numbers([year for _, year, _ in plan])
        records = [
            self._record(person, program, year, status, numbers[year].pop(0))
            for person, (program, year, status) in zip(people, plan, strict=True)
        ]
        StudentRecord.objects.bulk_create(records, batch_size=BATCH)

        guardians: list[Guardian] = []
        advisors: list[AdvisorAssignment] = []
        changes: list[StudentStatusChange] = []
        now = timezone.now().replace(microsecond=0)
        for index, record in enumerate(records):
            status = StudentStatus(record.status)
            if index % 3 == 0:
                guardians.append(
                    Guardian(
                        person_id=record.person_id,
                        relationship=self.rng.choice([GuardianRelationship.MOTHER, GuardianRelationship.FATHER]),
                        full_name=self.names.full_name(),
                        phone=f"010-{self.rng.randint(0, 9999):04d}-{self.rng.randint(0, 9999):04d}",
                        is_primary_contact=True,
                    )
                )
            if status.is_active():
                advisors.append(self._advisor(record, self.rng.choice(instructors[record.org_unit_id])))
            if leave is not None and status == StudentStatus.ENROLLED and index % 25 == 0:
                changes.append(
                    StudentStatusChange(
                        student_record=record,
                        type=leave,
                        from_status=StudentStatus.ENROLLED,
                        to_status=StudentStatus.ON_LEAVE,
                        effective_date=self.today + timedelta(weeks=2),
                        reason="Military service",
                        requested_at=now,
                    )
                )
        Guardian.objects.bulk_create(guardians, batch_size=BATCH)
        AdvisorAssignment.objects.bulk_create(advisors, batch_size=BATCH)
        StudentStatusChange.objects.bulk_create(changes, batch_size=BATCH)

    def _numbers(self, years: list[int]) -> dict[int, list[str]]:
        wanted: dict[int, int] = {}
        for year in years:
            wanted[year] = wanted.get(year, 0) + 1
        return {year: self.numbers.next_many(year, count) for year, count in sorted(wanted.items())}

    def _record(self, person: Person, program: Program, year: int, status: StudentStatus, number: str) -> StudentRecord:
        admission = date(year, 3, 1)
        return StudentRecord(
            person=person,
            student_number=number,
            program=program,
            org_unit_id=program.org_unit_id,
            admission_date=admission,
            catalog_year=year,
            year_level=min(4, max(1, self.today.year - year + 1)),
            status=status,
            status_changed_at=timezone.now().replace(microsecond=0),
            graduation_date=(date(year + 4, 3, 1) - timedelta(days=2) if status == StudentStatus.GRADUATED else None),
        )

    @staticmethod
    def _advisor(record: StudentRecord, instructor: Instructor) -> AdvisorAssignment:
        return AdvisorAssignment(
            student_record=record, instructor=instructor, role=AdvisorRole.PRIMARY, start_date=record.admission_date
        )

    # -- fixed portal accounts --------------------------------------------------------------------
    def fixed_accounts(self, programs: list[Program], instructors: dict[int, list[Instructor]]) -> None:
        domain = conf.DEMO_EMAIL_DOMAIN
        this_year = self.today.year
        program, last = programs[0], programs[-1]
        advisor = instructors[program.org_unit_id][0]
        self._account(advisor.person, f"instructor@{domain}")

        def single(email: str, program: Program, year: int, status: StudentStatus) -> tuple[Person, StudentRecord]:
            person = self.names.person(email, self.today)
            person.save()
            record = self._record(person, program, year, status, self.numbers.next(year))
            record.save()
            return person, record

        student, record = single(f"student@{domain}", program, this_year - 1, StudentStatus.ENROLLED)
        self._advisor(record, advisor).save()
        self._account(student, f"student@{domain}")

        graduate, _record = single(f"alumni@{domain}", program, this_year - 5, StudentStatus.GRADUATED)
        self._account(graduate, f"alumni@{domain}")

        readmitted, _old = single(f"readmitted@{domain}", program, this_year - 6, StudentStatus.GRADUATED)
        new = self._record(readmitted, last, this_year, StudentStatus.ENROLLED, self.numbers.next(this_year))
        new.save()
        self._advisor(new, instructors[last.org_unit_id][0]).save()
        self._account(readmitted, f"readmitted@{domain}")

    @staticmethod
    def _account(person: Person, email: str) -> None:
        user = User.objects.create_user(email=email, password=conf.DEMO_PASSWORD, person=person)
        user.email_verified_at = timezone.now().replace(microsecond=0)
        user.save(update_fields=["email_verified_at", "updated_at"])

    @classmethod
    def emails(cls) -> list[str]:
        return [f"{local}@{conf.DEMO_EMAIL_DOMAIN}" for local in cls.ACCOUNTS]


def _effective_units() -> Any:
    from ninefruits.organization.models import OrgUnit

    return OrgUnit.objects.effective_on()


def demo_people_emails() -> list[str]:
    return DemoPeopleSeeder.emails()


def enrolled_student_accounts() -> Iterator[tuple[str, str]]:
    """Accounts for load tests (``setup_demo --student-accounts``): one per enrolled student who
    has none, with the demo password (one password hash for all, bulk inserted)."""
    domain = conf.DEMO_EMAIL_DOMAIN
    password = make_password(conf.DEMO_PASSWORD)
    now = timezone.now().replace(microsecond=0)
    records = (
        StudentRecord.objects.filter(status=StudentStatus.ENROLLED)
        .select_related("person__user")
        .order_by("student_number")
    )
    missing: list[User] = []
    rows: list[tuple[str, str]] = []
    for record in records.iterator(chunk_size=BATCH):
        user = getattr(record.person, "user", None)
        if user is None:
            email = f"student{record.student_number}@{domain}"
            missing.append(User(email=email, password=password, person_id=record.person_id, email_verified_at=now))
        else:
            email = user.email
        rows.append((email, conf.DEMO_PASSWORD))
    User.objects.bulk_create(missing, batch_size=BATCH)
    yield from rows
