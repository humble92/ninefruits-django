from __future__ import annotations

from django.utils.module_loading import import_string

from ninefruits.setup.seeders.base import Seeder

from .options import current_options, ensure_not_production


class DemoSeeder(Seeder):
    """Fictional university for development, training and demonstrations. Each phase appends its
    demo seeder to ``SEEDERS`` in dependency order (porting-plan 13.4). Volumes are created with
    bulk inserts so even ``--size=large`` takes minutes, and every random choice comes from the
    options' generator, so ``--seed`` reproduces the data."""

    SEEDERS: list[str] = [
        "ninefruits.setup.seeders.demo.accounts.DemoAccountSeeder",
        "ninefruits.setup.seeders.demo.reference.DemoReferenceSeeder",
        "ninefruits.setup.seeders.demo.people.DemoPeopleSeeder",
        "ninefruits.setup.seeders.demo.admission.DemoAdmissionSeeder",
        "ninefruits.setup.seeders.demo.curriculum.DemoCurriculumSeeder",
        "ninefruits.setup.seeders.demo.grading.DemoGradeHistorySeeder",
        "ninefruits.setup.seeders.demo.registration.DemoRegistrationSeeder",
        "ninefruits.setup.seeders.demo.grading.DemoGradingSeeder",
    ]

    #: Functions returning the fixed demo account emails printed by ``setup_demo``.
    ACCOUNT_LISTS: list[str] = [
        "ninefruits.setup.seeders.demo.accounts.demo_account_emails",
        "ninefruits.setup.seeders.demo.people.demo_people_emails",
        "ninefruits.setup.seeders.demo.admission.demo_admission_emails",
    ]

    #: Functions yielding ``(email, password)`` of student accounts for ``--student-accounts``
    #: (Phase 2 adds the enrolled students).
    STUDENT_ACCOUNT_PROVIDERS: list[str] = ["ninefruits.setup.seeders.demo.people.enrolled_student_accounts"]

    def run(self) -> None:
        ensure_not_production()
        current_options()
        self.call(*(import_string(path) for path in self.SEEDERS))
